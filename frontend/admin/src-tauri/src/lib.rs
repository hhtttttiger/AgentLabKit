use rand::RngCore;
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::Manager;
use tauri_plugin_dialog::DialogExt;

struct LocalApiProcess(Mutex<Option<std::process::Child>>);
struct RuntimeConfigState(RuntimeConfig);

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConfigFile {
    mode: Option<String>,
    server_url: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConfig {
    mode: String,
    api_base_url: String,
    local_api_token: Option<String>,
}

fn read_runtime_config_file(app: &tauri::AppHandle) -> RuntimeConfigFile {
    app.path()
        .app_config_dir()
        .ok()
        .map(|path| path.join("config.json"))
        .and_then(|path| std::fs::read_to_string(path).ok())
        .and_then(|contents| serde_json::from_str::<RuntimeConfigFile>(&contents).ok())
        .unwrap_or_default()
}

fn read_mode_and_server_url(app: &tauri::AppHandle) -> (String, Option<String>) {
    let file_config = read_runtime_config_file(app);
    let mode = std::env::var("AGENTLAB_MODE")
        .ok()
        .or(file_config.mode)
        .unwrap_or_else(|| "local".to_string())
        .to_lowercase();
    let mode = if mode == "server" { "server" } else { "local" }.to_string();
    (mode, file_config.server_url)
}

fn server_runtime_config(app: &tauri::AppHandle) -> RuntimeConfig {
    let (mode, file_server_url) = read_mode_and_server_url(app);
    let api_base_url = if mode == "server" {
        std::env::var("AGENTLAB_SERVER_URL")
            .ok()
            .or(file_server_url)
            .or_else(|| std::env::var("VITE_API_BASE_URL").ok())
            .unwrap_or_default()
    } else {
        String::new()
    };
    RuntimeConfig {
        mode,
        api_base_url,
        local_api_token: None,
    }
}

fn allocate_local_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0))
        .map_err(|error| format!("failed to allocate local API port: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("failed to read allocated local API port: {error}"))
}

fn generate_local_token() -> String {
    let mut bytes = [0_u8; 32];
    rand::rng().fill_bytes(&mut bytes);
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn health_ready(port: u16) -> bool {
    let Ok(mut stream) =
        TcpStream::connect_timeout(&([127, 0, 0, 1], port).into(), Duration::from_millis(100))
    else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(100)));
    let request =
        format!("GET /health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n");
    let _ = stream.write_all(request.as_bytes());
    let mut response = [0_u8; 128];
    let size = stream.read(&mut response).unwrap_or(0);
    String::from_utf8_lossy(&response[..size]).contains(" 200 ")
}

fn wait_until_ready(child: &mut std::process::Child, port: u16) -> Result<(), String> {
    let deadline = Instant::now() + Duration::from_secs(10);
    while Instant::now() < deadline {
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("failed to inspect Local API process: {error}"))?
        {
            return Err(format!(
                "Local API exited before readiness (status: {status})"
            ));
        }
        if health_ready(port) {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    Err("Local API readiness timeout after 10 seconds".to_string())
}

#[tauri::command]
fn get_runtime_config(state: tauri::State<'_, RuntimeConfigState>) -> RuntimeConfig {
    state.0.clone()
}

#[tauri::command]
async fn pick_project_directory(app: tauri::AppHandle) -> Option<String> {
    app.dialog()
        .file()
        .blocking_pick_folder()
        .map(|path| path.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            get_runtime_config,
            pick_project_directory
        ])
        .setup(|app| {
            let (mode, _) = read_mode_and_server_url(app.handle());
            if mode == "server" {
                app.manage(LocalApiProcess(Mutex::new(None)));
                app.manage(RuntimeConfigState(server_runtime_config(app.handle())));
                return Ok(());
            }

            // Local Mode owns this embedded API process, its ephemeral port and
            // its process token. Readiness is established before the frontend
            // receives RuntimeConfig.
            let manifest_root = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let repo_root = std::env::var_os("AGENTLAB_REPO_ROOT")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|| manifest_root.join("../../.."));
            let python = if cfg!(windows) { "python" } else { "python3" };
            let python_path = [
                repo_root.join("desktop"),
                repo_root.join("packages/application/src"),
                repo_root.join("packages/agent_runtime/src"),
                repo_root.join("packages/evaluation/src"),
                repo_root.join("packages/llm_gateway/src"),
                repo_root.join("packages/infra/src"),
            ]
            .iter()
            .map(|path| path.to_string_lossy().to_string())
            .collect::<Vec<_>>()
            .join(if cfg!(windows) { ";" } else { ":" });

            let port = allocate_local_port()?;
            let token = generate_local_token();
            let mut child = std::process::Command::new(python)
                .args(["-m", "desktop.local.server"])
                .current_dir(&repo_root)
                .env("AGENTLAB_REPO_ROOT", &repo_root)
                .env("PYTHONPATH", python_path)
                .env("AGENTLAB_LOCAL_PORT", port.to_string())
                .env("AGENTLAB_LOCAL_TOKEN", &token)
                .spawn()
                .map_err(|error| format!("failed to start AgentLab Local Mode: {error}"))?;
            if let Err(error) = wait_until_ready(&mut child, port) {
                let _ = child.kill();
                let _ = child.wait();
                return Err(error.into());
            }

            app.manage(LocalApiProcess(Mutex::new(Some(child))));
            app.manage(RuntimeConfigState(RuntimeConfig {
                mode,
                api_base_url: format!("http://127.0.0.1:{port}"),
                local_api_token: Some(token),
            }));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building AgentLab Desktop")
        .run(|app_handle, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Ok(mut process) = app_handle.state::<LocalApiProcess>().0.lock() {
                    if let Some(mut child) = process.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        });
}

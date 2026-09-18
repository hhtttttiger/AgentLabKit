use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::Manager;

struct LocalApiProcess(Mutex<Option<std::process::Child>>);

#[derive(Debug, Default, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConfigFile {
    mode: Option<String>,
    server_url: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeConfig {
    mode: String,
    api_base_url: String,
}

fn read_runtime_config(app: &tauri::AppHandle) -> RuntimeConfig {
    let file_config = app
        .path()
        .app_config_dir()
        .ok()
        .map(|path| path.join("config.json"))
        .and_then(|path| std::fs::read_to_string(path).ok())
        .and_then(|contents| serde_json::from_str::<RuntimeConfigFile>(&contents).ok())
        .unwrap_or_default();

    let mode = std::env::var("AGENTLAB_MODE")
        .ok()
        .or(file_config.mode)
        .unwrap_or_else(|| "local".to_string())
        .to_lowercase();
    let mode = if mode == "server" { "server" } else { "local" }.to_string();

    let api_base_url = if mode == "server" {
        std::env::var("AGENTLAB_SERVER_URL")
            .ok()
            .or(file_config.server_url)
            .or_else(|| std::env::var("VITE_API_BASE_URL").ok())
            .unwrap_or_default()
    } else {
        "http://127.0.0.1:8000".to_string()
    };

    RuntimeConfig { mode, api_base_url }
}

#[tauri::command]
fn get_runtime_config(app: tauri::AppHandle) -> RuntimeConfig {
    read_runtime_config(&app)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_runtime_config])
        .setup(|app| {
            let runtime_config = read_runtime_config(app.handle());
            if runtime_config.mode == "server" {
                app.manage(LocalApiProcess(Mutex::new(None)));
                return Ok(());
            }

            // Local Mode is an embedded local API process, not a worker or a
            // server dependency. It owns the SQLite composition and exits
            // with the Desktop launcher in development/package environments
            // where Python is available.
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

            let child = std::process::Command::new(python)
                .args(["-m", "desktop.local.server"])
                .current_dir(&repo_root)
                .env("AGENTLAB_REPO_ROOT", &repo_root)
                .env("PYTHONPATH", python_path)
                .spawn()
                .map_err(|error| format!("failed to start AgentLab Local Mode: {error}"))?;
            app.manage(LocalApiProcess(Mutex::new(Some(child))));
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

import { invoke } from '@tauri-apps/api/core';

export type LocalProject = { path: string; displayName: string };

const PROJECT_KEY = 'agentlab-local-project';

export function loadLocalProject(): LocalProject | null {
  try {
    const value = window.localStorage.getItem(PROJECT_KEY);
    return value ? JSON.parse(value) as LocalProject : null;
  } catch {
    return null;
  }
}

export function saveLocalProject(project: LocalProject) {
  window.localStorage.setItem(PROJECT_KEY, JSON.stringify(project));
}

export function projectFromPath(path: string): LocalProject {
  const normalized = path.replace(/[\\/]$/, '');
  return { path, displayName: normalized.split(/[\\/]/).pop() || path };
}

export async function pickLocalProject(): Promise<LocalProject | null> {
  if (import.meta.env.VITE_DESKTOP_MODE === 'true') {
    const path = await invoke<string | null>('pick_project_directory');
    return path ? projectFromPath(path) : null;
  }

  return null;
}

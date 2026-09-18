import { invoke } from '@tauri-apps/api/core';

export type DesktopMode = 'local' | 'server';

export type RuntimeConfig = {
  mode: DesktopMode;
  apiBaseUrl: string;
};

const browserConfig: RuntimeConfig = {
  mode: 'server',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
};

let runtimeConfig = browserConfig;

export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  if (import.meta.env.VITE_DESKTOP_MODE !== 'true') {
    return runtimeConfig;
  }

  try {
    runtimeConfig = await invoke<RuntimeConfig>('get_runtime_config');
  } catch (error) {
    console.warn('[runtime] failed to load Tauri config, using build defaults', error);
  }

  return runtimeConfig;
}

export function getRuntimeConfig(): RuntimeConfig {
  return runtimeConfig;
}

export function isLocalDesktopMode(): boolean {
  return import.meta.env.VITE_DESKTOP_MODE === 'true' && runtimeConfig.mode === 'local';
}

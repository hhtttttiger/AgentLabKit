export type KbProvider = 'local' | 'azure';

export type KbSettingsFormState = {
  provider: KbProvider;
  local: {
    maxLength: number;
    overlap: number;
    splitter: string;
    indexes: string[];
  };
  recallSources: string[];
  azure: {
    profileId: string;
  };
  azureChunkPush: {
    batchSize: number;
  };
};

const DEFAULT_SETTINGS: KbSettingsFormState = {
  provider: 'local',
  local: {
    maxLength: 1024,
    overlap: 0,
    splitter: 'recursive',
    indexes: ['embedding', 'full_text'],
  },
  recallSources: [],
  azure: {
    profileId: 'azure-search-default',
  },
  azureChunkPush: {
    batchSize: 100,
  },
};

export function createDefaultKbSettings(): KbSettingsFormState {
  return {
    provider: DEFAULT_SETTINGS.provider,
    local: { ...DEFAULT_SETTINGS.local, indexes: [...DEFAULT_SETTINGS.local.indexes] },
    recallSources: [...DEFAULT_SETTINGS.recallSources],
    azure: { ...DEFAULT_SETTINGS.azure },
    azureChunkPush: { ...DEFAULT_SETTINGS.azureChunkPush },
  };
}

export function parseKbSettingsJson(settingsJson?: string | null): KbSettingsFormState {
  const defaults = createDefaultKbSettings();
  if (!settingsJson?.trim()) {
    return defaults;
  }

  try {
    const parsed = JSON.parse(settingsJson) as Record<string, unknown>;
    const provider = parsed.provider === 'azure' ? 'azure' : 'local';
    const local = typeof parsed.local === 'object' && parsed.local ? parsed.local as Record<string, unknown> : {};
    const azure = typeof parsed.azure === 'object' && parsed.azure ? parsed.azure as Record<string, unknown> : {};
    const azureChunkPush =
      typeof parsed.azureChunkPush === 'object' && parsed.azureChunkPush
        ? parsed.azureChunkPush as Record<string, unknown>
        : {};
    const recallSources = Array.isArray(parsed.recallSources)
      ? parsed.recallSources.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
      : [];

    return {
      provider,
      local: {
        maxLength: Number(local.maxLength ?? defaults.local.maxLength),
        overlap: Number(local.overlap ?? defaults.local.overlap),
        splitter: typeof local.splitter === 'string' && local.splitter.trim() ? local.splitter : defaults.local.splitter,
        indexes: Array.isArray(local.indexes)
          ? local.indexes.filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
          : defaults.local.indexes,
      },
      recallSources: provider === 'azure' ? [] : recallSources,
      azure: {
        profileId: typeof azure.profileId === 'string' ? azure.profileId : defaults.azure.profileId,
      },
      azureChunkPush: {
        batchSize: Number(azureChunkPush.batchSize ?? defaults.azureChunkPush.batchSize),
      },
    };
  } catch {
    return defaults;
  }
}

export function isAzureProfileRequiredAndMissing(settings: KbSettingsFormState): boolean {
  const needsAzureProfile =
    settings.provider === 'azure' || settings.recallSources.includes('azure_chunk_push');

  return needsAzureProfile && !settings.azure.profileId.trim();
}

export function serializeKbSettings(settings: KbSettingsFormState): string {
  const recallSources = settings.recallSources.includes('azure_chunk_push') ? ['azure_chunk_push'] : [];

  if (isAzureProfileRequiredAndMissing({ ...settings, recallSources })) {
    return '';
  }

  if (settings.provider === 'azure') {
    return JSON.stringify({
      version: 1,
      provider: 'azure',
      azure: {
        profileId: settings.azure.profileId.trim(),
      },
    });
  }

  const payload: Record<string, unknown> = {
    version: 1,
    provider: 'local',
    local: {
      maxLength: settings.local.maxLength,
      overlap: settings.local.overlap,
      splitter: settings.local.splitter,
      indexes: settings.local.indexes,
    },
    recallSources,
  };

  if (recallSources.length > 0) {
    payload.azure = {
      profileId: settings.azure.profileId.trim(),
    };
    payload.azureChunkPush = {
      batchSize: settings.azureChunkPush.batchSize,
    };
  }

  return JSON.stringify(payload);
}

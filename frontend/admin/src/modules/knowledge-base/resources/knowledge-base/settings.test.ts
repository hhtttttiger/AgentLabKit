import { describe, expect, it } from 'vitest';
import {
  createDefaultKbSettings,
  isAzureProfileRequiredAndMissing,
  parseKbSettingsJson,
  serializeKbSettings,
} from './settings';

describe('knowledge base settings', () => {
  it('requires azure profile for azure provider', () => {
    expect(
      serializeKbSettings({
        ...createDefaultKbSettings(),
        provider: 'azure',
        azure: { profileId: '' },
      }),
    ).toBe('');
  });

  it('requires azure profile for azure chunk push recall source', () => {
    expect(
      serializeKbSettings({
        ...createDefaultKbSettings(),
        recallSources: ['azure_chunk_push'],
        azure: { profileId: '' },
      }),
    ).toBe('');
  });

  it('treats whitespace-only azure profile as missing during serialization', () => {
    expect(
      serializeKbSettings({
        ...createDefaultKbSettings(),
        provider: 'azure',
        azure: { profileId: '   ' },
      }),
    ).toBe('');
  });

  it('reports azure profile as required and missing for the drawer gating rule', () => {
    expect(
      isAzureProfileRequiredAndMissing({
        ...createDefaultKbSettings(),
        provider: 'azure',
        azure: { profileId: '   ' },
      }),
    ).toBe(true);

    expect(
      isAzureProfileRequiredAndMissing({
        ...createDefaultKbSettings(),
        recallSources: ['azure_chunk_push'],
        azure: { profileId: 'azure-search-default' },
      }),
    ).toBe(false);
  });

  it('serializes local provider with azure chunk push', () => {
    const json = serializeKbSettings({
      provider: 'local',
      local: {
        maxLength: 1024,
        overlap: 128,
        splitter: 'recursive',
        indexes: ['embedding', 'full_text'],
      },
      recallSources: ['azure_chunk_push'],
      azure: { profileId: 'azure-search-default' },
      azureChunkPush: { batchSize: 100 },
    });

    expect(JSON.parse(json)).toEqual({
      version: 1,
      provider: 'local',
      local: {
        maxLength: 1024,
        overlap: 128,
        splitter: 'recursive',
        indexes: ['embedding', 'full_text'],
      },
      recallSources: ['azure_chunk_push'],
      azure: { profileId: 'azure-search-default' },
      azureChunkPush: { batchSize: 100 },
    });
  });

  it('drops recall sources when provider is azure', () => {
    const parsed = parseKbSettingsJson('{"version":1,"provider":"azure","azure":{"profileId":"azure-search-default"}}');

    expect(parsed.provider).toBe('azure');
    expect(parsed.recallSources).toEqual([]);
  });

  it('creates stable defaults for local provider editing', () => {
    expect(createDefaultKbSettings()).toEqual({
      provider: 'local',
      local: {
        maxLength: 1024,
        overlap: 0,
        splitter: 'recursive',
        indexes: ['embedding', 'full_text'],
      },
      recallSources: [],
      azure: { profileId: 'azure-search-default' },
      azureChunkPush: { batchSize: 100 },
    });
  });

  it('uses default azure profile when settingsJson is empty', () => {
    expect(parseKbSettingsJson()).toMatchObject({
      provider: 'local',
      azure: { profileId: 'azure-search-default' },
    });
  });
});

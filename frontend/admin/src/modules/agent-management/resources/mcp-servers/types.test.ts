import { describe, expect, it } from 'vitest';
import { filterMcpServerRows, mapMcpServer, toMcpServerApiCreateRequest } from './types';

describe('mcp server type helpers', () => {
  it('maps API config fields into a summary view', () => {
    const result = mapMcpServer({
      id: '1',
      name: 'filesystem',
      displayName: 'filesystem',
      transportType: 'http',
      url: 'http://localhost:3000/mcp',
      headersJson: { toolNamePrefix: 'fs_', tags: ['prod'] },
      isEnabled: true,
      createdAtUtc: '2026-04-08T00:00:00Z',
    });

    expect(result.endpoint).toBe('http://localhost:3000/mcp');
    expect(result.toolNamePrefix).toBe('fs_');
    expect(result.tags).toEqual(['prod']);
  });

  it('merges primary form fields back into backend config', () => {
    const result = toMcpServerApiCreateRequest({
      name: 'filesystem',
      transport: 'stdio',
      endpoint: null,
      command: 'npx',
      isEnabled: true,
      toolNamePrefix: 'fs_',
      tags: ['prod'],
      config: { args: ['-y', '@modelcontextprotocol/server-filesystem'] },
    });

    expect(result).toEqual({
      name: 'filesystem',
      displayName: 'filesystem',
      transportType: 'stdio',
      url: null,
      headersJson: {
        args: ['-y', '@modelcontextprotocol/server-filesystem'],
        toolNamePrefix: 'fs_',
        tags: ['prod'],
      },
      isEnabled: true,
    });
  });

  it('filters rows locally by transport and fuzzy search', () => {
    const rows = filterMcpServerRows([
      {
        id: '1',
        name: 'filesystem',
        transport: 'stdio',
        endpoint: null,
        command: 'npx',
        toolNamePrefix: 'fs_',
        tags: ['local'],
        isEnabled: true,
        config: {},
        createdAtUtc: '',
        updatedAtUtc: null,
      },
      {
        id: '2',
        name: 'postgres',
        transport: 'http',
        endpoint: 'http://localhost:3001/mcp',
        command: null,
        toolNamePrefix: null,
        tags: ['db'],
        isEnabled: true,
        config: {},
        createdAtUtc: '',
        updatedAtUtc: null,
      },
    ], {
      transport: 'http',
      search: '3001',
      page: 1,
      pageSize: 20,
    });

    expect(rows).toHaveLength(1);
    expect(rows[0]?.name).toBe('postgres');
  });
});

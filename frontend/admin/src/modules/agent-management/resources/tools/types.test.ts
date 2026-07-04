import { describe, expect, it } from 'vitest';
import {
  defaultToolFilters,
  filterToolRows,
  paginateRows,
  toToolListQuery,
  type ToolSummaryView,
} from './types';

function makeTool(overrides: Partial<ToolSummaryView> = {}): ToolSummaryView {
  return {
    id: 'id-1',
    toolName: 'knowledge_search',
    displayName: 'Knowledge Search',
    description: 'Search the knowledge base.',
    sourceType: 'builtin',
    parametersSchema: {},
    tags: ['rag', 'read_only'],
    endpointUrl: null,
    httpMethod: 'POST',
    credentialKey: null,
    timeoutSeconds: 10,
    maxRetries: 0,
    status: 'active',
    createdAtUtc: '2026-01-01T00:00:00Z',
    updatedAtUtc: null,
    ...overrides,
  };
}

describe('toToolListQuery', () => {
  it('returns empty object for default filters (except status=active)', () => {
    const filters = { ...defaultToolFilters, status: '' as const };
    const query = toToolListQuery(filters);
    expect(query).toEqual({});
  });

  it('includes sourceType when set', () => {
    const query = toToolListQuery({ ...defaultToolFilters, sourceType: 'builtin', status: '' });
    expect(query.sourceType).toBe('builtin');
  });

  it('includes status when set', () => {
    const query = toToolListQuery({ ...defaultToolFilters, status: 'active', sourceType: '' });
    expect(query.status).toBe('active');
  });

  it('includes search when non-empty', () => {
    const query = toToolListQuery({ ...defaultToolFilters, search: '  crm  ', status: '' });
    expect(query.search).toBe('crm');
  });
});

describe('filterToolRows', () => {
  const tools: ToolSummaryView[] = [
    makeTool({ toolName: 'knowledge_search', sourceType: 'builtin', status: 'active' }),
    makeTool({ id: 'id-2', toolName: 'crm_lookup', displayName: 'CRM Lookup', sourceType: 'http_external', status: 'active', tags: ['crm'] }),
    makeTool({ id: 'id-3', toolName: 'old_tool', displayName: 'Old Tool', sourceType: 'http_external', status: 'disabled', tags: [] }),
  ];

  it('returns all rows when no filters', () => {
    const filters = { ...defaultToolFilters, sourceType: '' as const, status: '' as const, search: '' };
    expect(filterToolRows(tools, filters)).toHaveLength(3);
  });

  it('filters by sourceType', () => {
    const filters = { ...defaultToolFilters, sourceType: 'builtin' as const, status: '' as const, search: '' };
    const result = filterToolRows(tools, filters);
    expect(result).toHaveLength(1);
    expect(result[0].toolName).toBe('knowledge_search');
  });

  it('filters by status', () => {
    const filters = { ...defaultToolFilters, sourceType: '' as const, status: 'disabled' as const, search: '' };
    const result = filterToolRows(tools, filters);
    expect(result).toHaveLength(1);
    expect(result[0].toolName).toBe('old_tool');
  });

  it('filters by search on toolName', () => {
    const filters = { ...defaultToolFilters, sourceType: '' as const, status: '' as const, search: 'crm' };
    const result = filterToolRows(tools, filters);
    expect(result).toHaveLength(1);
    expect(result[0].toolName).toBe('crm_lookup');
  });

  it('filters by search on displayName', () => {
    const filters = { ...defaultToolFilters, sourceType: '' as const, status: '' as const, search: 'Knowledge Search' };
    const result = filterToolRows(tools, filters);
    expect(result).toHaveLength(1);
    expect(result[0].toolName).toBe('knowledge_search');
  });
});

describe('paginateRows', () => {
  const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  it('returns first page', () => {
    expect(paginateRows(items, 1, 3)).toEqual([1, 2, 3]);
  });

  it('returns second page', () => {
    expect(paginateRows(items, 2, 3)).toEqual([4, 5, 6]);
  });

  it('returns partial last page', () => {
    expect(paginateRows(items, 4, 3)).toEqual([10]);
  });

  it('returns empty for page beyond total', () => {
    expect(paginateRows(items, 10, 3)).toEqual([]);
  });
});

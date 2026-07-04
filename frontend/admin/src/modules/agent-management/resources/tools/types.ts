// Tool definition source type
export type ToolSourceType = 'builtin' | 'http_external';

// Tool status lifecycle
export type ToolStatus = 'active' | 'deprecated' | 'disabled';

// ── API view types (from /api/agent-tools/definitions) ──────────────────────

export type ToolDefinitionApiView = {
  id: string;
  toolName: string;
  displayName: string;
  description: string;
  sourceType: ToolSourceType;
  parametersSchema: Record<string, unknown>;
  tags: string[];
  endpointUrl: string | null;
  httpMethod: string;
  credentialKey: string | null;
  timeoutSeconds: number;
  maxRetries: number;
  status: ToolStatus;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type VersionToolBindingApiView = {
  id: string;
  toolName: string;
  displayName: string | null;
  description: string | null;
  invocationMode: 'auto' | 'manual_only' | 'disabled';
  isRequired: boolean;
  sortOrder: number;
  isEnabled: boolean;
  config: Record<string, unknown>;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

// ── Form / draft types (used in ToolDrawer) ──────────────────────────────────

export type CreateToolDefinitionRequest = {
  toolName: string;
  displayName: string;
  description: string;
  endpointUrl: string;
  parametersSchema: Record<string, unknown>;
  tags: string[];
  httpMethod: string;
  credentialKey: string | null;
  timeoutSeconds: number;
  maxRetries: number;
};

export type UpdateToolDefinitionRequest = Omit<CreateToolDefinitionRequest, 'toolName'>;

// ── Filter / view model ──────────────────────────────────────────────────────

export type ToolFilters = {
  sourceType: '' | ToolSourceType;
  status: '' | ToolStatus;
  search: string;
  page: number;
  pageSize: number;
};

export const defaultToolFilters: ToolFilters = {
  sourceType: '',
  status: 'active',
  search: '',
  page: 1,
  pageSize: 20,
};

export type ToolListQuery = {
  sourceType?: string;
  status?: string;
  search?: string;
};

// ── View model helpers ────────────────────────────────────────────────────────

/**
 * Convenience view for the list page. Adds derived display fields.
 */
export type ToolSummaryView = ToolDefinitionApiView;

export function toToolListQuery(filters: ToolFilters): ToolListQuery {
  return {
    ...(filters.sourceType ? { sourceType: filters.sourceType } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...((filters.search ?? '').trim() ? { search: (filters.search ?? '').trim() } : {}),
  };
}

export function filterToolRows(rows: ToolSummaryView[], filters: ToolFilters) {
  const search = (filters.search ?? '').trim().toLowerCase();

  return rows.filter((row) => {
    if (filters.sourceType && row.sourceType !== filters.sourceType) return false;
    if (filters.status && row.status !== filters.status) return false;
    if (!search) return true;

    return [row.toolName, row.displayName, row.description, ...row.tags]
      .some((value) => value.toLowerCase().includes(search));
  });
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

export const emptyToolDraft: CreateToolDefinitionRequest = {
  toolName: '',
  displayName: '',
  description: '',
  endpointUrl: '',
  parametersSchema: { type: 'object', properties: {} },
  tags: [],
  httpMethod: 'POST',
  credentialKey: null,
  timeoutSeconds: 30,
  maxRetries: 0,
};

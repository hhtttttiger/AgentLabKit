export type McpTransport = 'stdio' | 'sse' | 'http';

export type McpServerApiView = {
  id: string;
  name: string;
  displayName: string;
  transportType: string;
  url: string | null;
  headersJson: Record<string, unknown>;
  isEnabled: boolean;
  createdAtUtc: string;
};

export type McpServerSummaryView = {
  id: string;
  name: string;
  transport: McpTransport;
  endpoint: string | null;
  command: string | null;
  toolNamePrefix: string | null;
  tags: string[];
  isEnabled: boolean;
  config: Record<string, unknown>;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type McpServerDetailView = McpServerSummaryView;

export type McpServerListQuery = {
  activeOnly?: boolean;
  page?: number;
  pageSize?: number;
};

export type CreateMcpServerRequest = {
  name: string;
  transport: McpTransport;
  endpoint: string | null;
  command: string | null;
  isEnabled: boolean;
  toolNamePrefix: string | null;
  tags: string[];
  config: Record<string, unknown>;
};

export type UpdateMcpServerRequest = Omit<CreateMcpServerRequest, 'name'>;

export type CreateMcpServerApiRequest = {
  name: string;
  displayName: string;
  transportType: string;
  url: string | null;
  headersJson: Record<string, unknown>;
  isEnabled: boolean;
};

export type UpdateMcpServerApiRequest = {
  displayName?: string;
  transportType?: string;
  url?: string | null;
  headersJson?: Record<string, unknown>;
  isEnabled?: boolean;
};

export type McpBindingApiView = {
  id: string;
  serverName: string;
  isEnabled: boolean;
  toolWhitelist: string[] | null;
  configOverrides: Record<string, unknown>;
  createdAtUtc: string;
  updatedAtUtc: string | null;
};

export type McpBindingApiRequest = {
  serverName: string;
  isEnabled: boolean;
  toolWhitelist: string[] | null;
  configOverrides: Record<string, unknown>;
};

export type McpServerFilters = {
  transport: '' | McpTransport;
  search: string;
  page: number;
  pageSize: number;
};

export const defaultMcpServerFilters: McpServerFilters = {
  transport: '',
  search: '',
  page: 1,
  pageSize: 20,
};

export function toMcpServerListQuery(filters: McpServerFilters): McpServerListQuery {
  void filters;
  return {};
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : [];
}

export function mapMcpServer(api: McpServerApiView): McpServerSummaryView {
  return {
    id: api.id,
    name: api.name,
    transport: api.transportType as McpTransport,
    endpoint: api.url,
    command: null,
    toolNamePrefix: asString(api.headersJson?.toolNamePrefix),
    tags: asStringArray(api.headersJson?.tags),
    isEnabled: api.isEnabled,
    config: api.headersJson,
    createdAtUtc: api.createdAtUtc,
    updatedAtUtc: null,
  };
}

export function toMcpServerApiCreateRequest(draft: CreateMcpServerRequest): CreateMcpServerApiRequest {
  const headersJson: Record<string, unknown> = {
    ...draft.config,
    ...(draft.toolNamePrefix?.trim() ? { toolNamePrefix: draft.toolNamePrefix.trim() } : {}),
    ...(draft.tags.length > 0 ? { tags: draft.tags } : {}),
  };

  return {
    name: (draft.name ?? '').trim(),
    displayName: (draft.name ?? '').trim(),
    transportType: draft.transport,
    url: draft.transport === 'stdio' ? null : draft.endpoint?.trim() || null,
    headersJson: Object.fromEntries(Object.entries(headersJson).filter(([, value]) => value !== undefined)),
    isEnabled: draft.isEnabled,
  };
}

export function toMcpServerApiUpdateRequest(draft: UpdateMcpServerRequest): UpdateMcpServerApiRequest {
  const headersJson: Record<string, unknown> = {
    ...draft.config,
    ...(draft.toolNamePrefix?.trim() ? { toolNamePrefix: draft.toolNamePrefix.trim() } : {}),
    ...(draft.tags.length > 0 ? { tags: draft.tags } : {}),
  };

  return {
    transportType: draft.transport,
    url: draft.transport === 'stdio' ? null : draft.endpoint?.trim() || null,
    headersJson: Object.fromEntries(Object.entries(headersJson).filter(([, value]) => value !== undefined)),
    isEnabled: draft.isEnabled,
  };
}

export function filterMcpServerRows(rows: McpServerSummaryView[], filters: McpServerFilters) {
  const search = (filters.search ?? '').trim().toLowerCase();

  return rows.filter((row) => {
    if (filters.transport && row.transport !== filters.transport) {
      return false;
    }

    if (!search) {
      return true;
    }

    return [
      row.name,
      row.endpoint ?? '',
      row.command ?? '',
      row.toolNamePrefix ?? '',
      ...row.tags,
    ].some((value) => value.toLowerCase().includes(search));
  });
}

export function paginateRows<T>(rows: T[], page: number, pageSize: number) {
  const start = (page - 1) * pageSize;
  return rows.slice(start, start + pageSize);
}

export const emptyMcpServerDraft: CreateMcpServerRequest = {
  name: '',
  transport: 'http',
  endpoint: null,
  command: null,
  isEnabled: true,
  toolNamePrefix: null,
  tags: [],
  config: {},
};

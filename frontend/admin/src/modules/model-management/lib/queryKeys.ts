export const modelManagementQueryKeys = {
  connectionProfiles: (suffix: string, query?: unknown) => ['model-management', 'connection-profiles', suffix, query] as const,
  models: (suffix: string, query?: unknown) => ['model-management', 'models', suffix, query] as const,
  modelInstances: (suffix: string, query?: unknown) => ['model-management', 'model-instances', suffix, query] as const,
  modelBindings: (suffix: string, query?: unknown) => ['model-management', 'model-bindings', suffix, query] as const,
  features: (suffix: string, query?: unknown) => ['model-management', 'features', suffix, query] as const,
};

/** Stale time constants for React Query caching strategy.
 *  List queries change with filters — short stale window to balance freshness vs requests.
 *  Detail views change less often. Options (dropdown enums) rarely change. */
export const modelManagementStaleTime = {
  list: 30_000,
  detail: 5 * 60_000,
  options: 10 * 60_000,
} as const;

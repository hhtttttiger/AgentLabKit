export const modelMonitoringQueryKeys = {
  usage: (suffix: string, query?: unknown) => ['model-monitoring', 'usage', suffix, query] as const,
  errors: (suffix: string, query?: unknown) => ['model-monitoring', 'errors', suffix, query] as const,
};

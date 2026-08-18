export const observabilityQueryKeys = {
  traces: (query?: unknown) => ['observability', 'traces', query] as const,
  traceDetail: (traceId: string) => ['observability', 'trace', traceId] as const,
  stats: (days: number) => ['observability', 'stats', days] as const,
  ingestionHealth: () => ['observability', 'ingestion-health'] as const,
};

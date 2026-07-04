export const observabilityQueryKeys = {
  traces: (query?: unknown) => ['observability', 'traces', query] as const,
  traceDetail: (traceId: string) => ['observability', 'trace', traceId] as const,
  traceTimeline: (traceId: string) => ['observability', 'timeline', traceId] as const,
  stats: (days: number) => ['observability', 'stats', days] as const,
};

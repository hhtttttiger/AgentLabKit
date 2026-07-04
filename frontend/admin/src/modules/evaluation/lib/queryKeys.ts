export const evaluationQueryKeys = {
  datasets: () => ['evaluation', 'datasets'] as const,
  cases: (datasetId: string) => ['evaluation', 'cases', datasetId] as const,
  configs: () => ['evaluation', 'configs'] as const,
  runs: () => ['evaluation', 'runs'] as const,
  runDetail: (runId: string) => ['evaluation', 'run', runId] as const,
};

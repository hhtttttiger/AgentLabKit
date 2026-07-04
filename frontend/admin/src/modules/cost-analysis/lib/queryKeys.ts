export const costAnalysisQueryKeys = {
  overview: (days: number) => ['cost-analysis', 'overview', days] as const,
  breakdownByModel: (days: number) => ['cost-analysis', 'breakdown', 'model', days] as const,
  breakdownByCapability: (days: number) => ['cost-analysis', 'breakdown', 'capability', days] as const,
  trend: (granularity: string, days: number) => ['cost-analysis', 'trend', granularity, days] as const,
  budgets: () => ['cost-analysis', 'budgets'] as const,
  alerts: (acknowledged?: boolean | null) => ['cost-analysis', 'alerts', acknowledged] as const,
};

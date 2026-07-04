// ── TypeScript 类型 ────────────────────────────────────────────────

export interface CostOverviewData {
  totalSpend: number;
  totalRequests: number;
  totalTokens: number;
  avgLatencyMs: number;
  periodStart: string;
  periodEnd: string;
  prevTotalSpend: number;
  prevTotalRequests: number;
  spendChangePct: number;
  topModels: CostBreakdownItem[];
  totalCacheWriteTokens?: number;
  totalCacheReadTokens?: number;
}

export interface CostBreakdownItem {
  scope: string;
  totalRequests: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalEstimatedCost: number;
  avgLatencyMs: number;
  totalCacheWriteTokens?: number;
  totalCacheReadTokens?: number;
}

export interface CostTrendPoint {
  period: string;
  totalCost: number;
  totalTokens: number;
  requestCount: number;
  totalCacheWriteTokens?: number;
  totalCacheReadTokens?: number;
}

export interface BudgetData {
  id: string;
  scopeType: string;
  scopeKey: string;
  monthlyLimitUsd: number;
  alertThresholdPct: number;
  isEnabled: boolean;
  createdAtUtc: string;
  updatedAtUtc: string;
}

export interface AlertData {
  id: string;
  budgetId: string;
  scopeType: string;
  scopeKey: string;
  alertType: string;
  currentSpendUsd: number;
  thresholdUsd: number;
  triggeredAtUtc: string;
  acknowledgedAtUtc: string | null;
}

export type Granularity = 'day' | 'week' | 'month';

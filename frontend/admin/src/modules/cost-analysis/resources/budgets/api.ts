import { apiRequest } from '@/shared/api/client';
import type { BudgetData } from '../../lib/contracts';

// ── 通用下拉选项类型 ─────────────────────────────────────────────────

export interface OptionItem {
  value: string;
  label: string;
}

// ── 预算 CRUD ────────────────────────────────────────────────────────

export function listBudgets() {
  return apiRequest<BudgetData[]>('/api/cost/budgets');
}

export function createBudget(body: {
  scopeType: string;
  scopeKey?: string;
  monthlyLimitUsd: number;
  alertThresholdPct?: number;
  isEnabled?: boolean;
}) {
  return apiRequest<BudgetData>('/api/cost/budgets', { method: 'POST', body });
}

export function updateBudget(id: string, body: {
  monthlyLimitUsd?: number;
  alertThresholdPct?: number;
  isEnabled?: boolean;
}) {
  return apiRequest<BudgetData>(`/api/cost/budgets/${id}`, { method: 'PUT', body });
}

export function deleteBudget(id: string) {
  return apiRequest<void>(`/api/cost/budgets/${id}`, { method: 'DELETE' });
}

// ── 范围选项查询 ────────────────────────────────────────────────────

export function fetchModelOptions() {
  return apiRequest<OptionItem[]>('/api/llm-catalog/models/options');
}

export function fetchAgentOptions() {
  return apiRequest<OptionItem[]>('/api/agents/options');
}

export function fetchUserOptions() {
  return apiRequest<OptionItem[]>('/api/auth/users');
}

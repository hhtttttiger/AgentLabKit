import { formatAdminDateTime } from '@/shared/i18n/formatters';

/** 延迟格式化。 */
export function formatDuration(ms: number | null): string {
  if (ms == null) return '—';
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

/** Span kind 显示标签。 */
const KIND_LABELS: Record<string, string> = {
  agent_turn: 'Agent Turn',
  llm_call: 'LLM 调用',
  tool_execution: '工具执行',
  rag_query: 'RAG 查询',
  handoff: 'Handoff',
  guardrail: 'Guardrail',
};

/** Source-type qualifier for tool_execution spans. */
const TOOL_SOURCE_LABELS: Record<string, string> = {
  mcp: 'MCP 工具',
  http_external: 'HTTP 工具',
  builtin: '内置工具',
};

export function formatSpanKind(kind: string, attributes?: Record<string, unknown>): string {
  if (kind === 'tool_execution' && attributes) {
    const sourceType = String(attributes.source_type || '');
    if (sourceType && TOOL_SOURCE_LABELS[sourceType]) {
      return TOOL_SOURCE_LABELS[sourceType];
    }
  }
  return KIND_LABELS[kind] || kind;
}

/** Span kind 对应颜色（RGB）。 */
const KIND_COLORS: Record<string, string> = {
  agent_turn: '59 130 246',     // blue
  llm_call: '139 92 246',      // violet
  tool_execution: '20 184 166', // teal
  rag_query: '245 158 11',     // amber
  handoff: '236 72 153',       // pink
  guardrail: '239 68 68',      // red
};

export function getSpanKindColor(kind: string): string {
  return KIND_COLORS[kind] || '148 163 184'; // default slate
}

/** 时间偏移格式化。 */
export function formatTimeOffset(offsetMs: number): string {
  if (offsetMs >= 1000) return `+${(offsetMs / 1000).toFixed(2)}s`;
  return `+${Math.round(offsetMs)}ms`;
}

/** 统一日期时间格式化（带前导零）。 */
export function formatDateTime(value: string | null | undefined): string {
  return formatAdminDateTime(value, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

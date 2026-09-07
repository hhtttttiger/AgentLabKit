import type {
  AgentExecutionTrace,
  AgentTraceStep,
  AgentTraceToolEvent,
  AgentTraceAppliedSkill,
  AgentTraceUsage,
  AgentTraceRetrievalEvent,
  AgentTraceRetrievalResult,
} from '@/shared/agent-trace/contracts';
import type { TraceDetailResponse, SpanData } from '@/modules/observability/lib/contracts';

const AGENT_SPAN_KINDS = new Set(['agent', 'llm', 'tool', 'chain', 'retrieval']);

function nullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function nullableNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function extractRetrievalEvent(span: SpanData): AgentTraceRetrievalEvent {
  const attrs = span.attributes;
  const rawResults = Array.isArray(attrs['retrieval.results']) ? attrs['retrieval.results'] : [];
  const results: AgentTraceRetrievalResult[] = rawResults.map((raw) => {
    const result = raw && typeof raw === 'object' ? raw as Record<string, unknown> : {};
    return {
      knowledgeBaseId: nullableString(result.knowledge_base_id),
      documentId: nullableString(result.document_id),
      segmentId: nullableString(result.segment_id),
      score: nullableNumber(result.score),
      title: nullableString(result.title),
      source: nullableString(result.source),
      contentPreview: nullableString(result.content_preview),
    };
  });
  return {
    status: span.status === 'ok' ? 'succeeded' : 'failed',
    query: nullableString(attrs['retrieval.query']),
    source: nullableString(attrs['retrieval.source']),
    knowledgeBaseIds: Array.isArray(attrs['retrieval.knowledge_base_ids'])
      ? attrs['retrieval.knowledge_base_ids'].filter((value): value is string => typeof value === 'string')
      : [],
    topK: nullableNumber(attrs['retrieval.top_k']),
    searchMode: nullableString(attrs['retrieval.search_mode']),
    resultCount: nullableNumber(attrs['retrieval.result_count']),
    durationMs: nullableNumber(attrs['retrieval.duration_ms']) ?? span.durationMs,
    results,
    errorMessage: nullableString(attrs['retrieval.error_message']) ?? span.errorMessage ?? null,
  };
}

function extractToolEvent(span: SpanData): AgentTraceToolEvent | null {
  const attrs = span.attributes;
  const toolName = (attrs['tool.name'] as string) ?? span.name;
  return {
    toolName,
    displayName: (attrs['tool.display_name'] as string) ?? toolName,
    status: span.status === 'ok' ? 'succeeded' : 'failed',
    arguments: (attrs['tool.arguments'] as Record<string, unknown>) ?? {},
    outputText: (attrs['tool.output'] as string) ?? null,
    errorMessage: span.errorMessage ?? null,
    sourceType: (attrs['tool.source_type'] as string) ?? null,
    sourceRef: (attrs['tool.source_ref'] as string) ?? null,
    tags: (attrs['tool.tags'] as string[]) ?? [],
    durationMs: span.durationMs,
  };
}

function spanToStep(span: SpanData): AgentTraceStep | null {
  const kind = span.kind?.toLowerCase() ?? '';
  if (!AGENT_SPAN_KINDS.has(kind)) return null;

  if (kind === 'retrieval') {
    const retrievalEvent = extractRetrievalEvent(span);
    return {
      type: 'retrieval',
      status: retrievalEvent.status,
      title: retrievalEvent.status === 'failed' ? 'Retrieval failed' : 'Retrieval',
      retrievalEvent,
    };
  }

  const toolEvent = extractToolEvent(span);
  const attrs = span.attributes;

  if (kind === 'tool') {
    return {
      type: 'tool_call',
      status: span.status === 'ok' ? 'succeeded' : 'failed',
      title: (attrs['tool.display_name'] as string) ?? span.name,
      toolEvent,
    };
  }

  if (kind === 'llm') {
    return {
      type: 'reply_completed',
      status: span.status === 'ok' ? 'succeeded' : 'failed',
      title: span.name,
      replyText: (attrs['llm.output_text'] as string) ?? null,
    };
  }

  if (kind === 'agent') {
    return {
      type: 'context',
      status: 'ready',
      title: span.name,
      appliedSkills: (attrs['agent.applied_skills'] as AgentTraceAppliedSkill[]) ?? [],
    };
  }

  return {
    type: 'chain',
    status: span.status === 'ok' ? 'succeeded' : 'failed',
    title: span.name,
  };
}

function extractUsage(trace: { totalInputTokens: number; totalOutputTokens: number }): AgentTraceUsage {
  return {
    inputTokens: trace.totalInputTokens,
    outputTokens: trace.totalOutputTokens,
    totalTokens: trace.totalInputTokens + trace.totalOutputTokens,
  };
}

export function mapTraceToAgentExecution(detail: TraceDetailResponse): AgentExecutionTrace {
  const { trace, spans } = detail;
  const toolEvents: AgentTraceToolEvent[] = [];
  const retrievalEvents: AgentTraceRetrievalEvent[] = [];
  const steps: AgentTraceStep[] = [];

  for (const span of spans) {
    const kind = span.kind?.toLowerCase() ?? '';
    if (!AGENT_SPAN_KINDS.has(kind)) continue;

    const step = spanToStep(span);
    if (step) steps.push(step);

    if (kind === 'tool') {
      const toolEvent = extractToolEvent(span);
      if (toolEvent) toolEvents.push(toolEvent);
    }
    if (kind === 'retrieval' && step?.retrievalEvent) {
      retrievalEvents.push(step.retrievalEvent);
    }
  }

  const agentSpan = spans.find(
    (s) => s.kind?.toLowerCase() === 'agent',
  );
  const agentAttrs = agentSpan?.attributes ?? {};

  return {
    runId: trace.runId,
    // These fields are optional in the Trace API. Do not infer them from span
    // attributes or substitute a made-up session/action value.
    sessionId: trace.sessionId,
    traceId: trace.traceId,
    agentKey: trace.agentKey,
    agentVersion: typeof agentAttrs['agent.version'] === 'number' ? agentAttrs['agent.version'] : null,
    status: trace.status === 'ok' ? 'succeeded' : trace.status,
    action: typeof agentAttrs['agent.action'] === 'string' ? agentAttrs['agent.action'] : null,
    replyText: null,
    handoffReason: null,
    errorCode: null,
    errorMessage: null,
    appliedSkills: (agentAttrs['agent.applied_skills'] as AgentTraceAppliedSkill[]) ?? [],
    toolEvents,
    retrievalEvents,
    steps,
    usage: extractUsage(trace),
    startedAtUtc: trace.startedAtUtc,
    completedAtUtc: trace.completedAtUtc,
  };
}

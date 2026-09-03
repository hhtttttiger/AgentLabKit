import type {
  AgentExecutionTrace,
  AgentTraceStep,
  AgentTraceToolEvent,
  AgentTraceAppliedSkill,
  AgentTraceUsage,
} from '@/shared/agent-trace/contracts';
import type { TraceDetailResponse, SpanData } from '@/modules/observability/lib/contracts';

const AGENT_SPAN_KINDS = new Set(['agent', 'llm', 'tool', 'chain']);

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
    steps,
    usage: extractUsage(trace),
    startedAtUtc: trace.startedAtUtc,
    completedAtUtc: trace.completedAtUtc,
  };
}

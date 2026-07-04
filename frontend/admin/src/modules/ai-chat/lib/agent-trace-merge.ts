import type { AgentExecutionTrace, AgentTraceStep } from '@/shared/agent-trace/contracts';
import type { AgentChatMessageInput, AgentStreamEvent } from './contracts';

export function mergeAgentTrace(
  current: AgentExecutionTrace | null,
  event: AgentStreamEvent,
  fallbackAgentKey: string,
): AgentExecutionTrace {
  const nextReplyText = event.replyText ?? (
    event.type === 'reply_delta'
      ? `${current?.replyText ?? ''}${event.delta ?? ''}`
      : current?.replyText
  );
  const nextSteps = buildNextSteps(current?.steps ?? [], event);
  const nextToolEvents = event.toolEvent
    ? [...(current?.toolEvents ?? []), event.toolEvent]
    : current?.toolEvents ?? [];

  return {
    runId: event.runId,
    sessionId: event.sessionId,
    traceId: event.traceId,
    agentKey: event.agentKey ?? current?.agentKey ?? fallbackAgentKey,
    agentVersion: event.agentVersion ?? current?.agentVersion ?? 0,
    status: event.status ?? current?.status ?? 'running',
    action: event.action ?? current?.action ?? 'reply',
    replyText: nextReplyText,
    handoffReason: event.handoffReason ?? current?.handoffReason ?? null,
    errorCode: event.errorCode ?? current?.errorCode ?? null,
    errorMessage: event.errorMessage ?? current?.errorMessage ?? null,
    appliedSkills: event.appliedSkills ?? current?.appliedSkills ?? [],
    toolEvents: nextToolEvents,
    steps: nextSteps,
    usage: event.usage ?? current?.usage ?? null,
  };
}

function buildNextSteps(previous: AgentTraceStep[], event: AgentStreamEvent) {
  const nextStep = buildStepFromEvent(event);
  return nextStep ? [...previous, nextStep] : previous;
}

export function buildStepFromEvent(event: AgentStreamEvent): AgentTraceStep | null {
  switch (event.type) {
    case 'context':
      return {
        type: 'context',
        status: 'ready',
        title: 'Agent context ready',
        appliedSkills: event.appliedSkills ?? [],
      };
    case 'tool_call':
      return {
        type: 'tool_call',
        status: 'running',
        title: event.toolEvent?.displayName ?? event.toolEvent?.toolName ?? 'Tool call',
        toolEvent: event.toolEvent ?? null,
      };
    case 'tool_result':
      return {
        type: 'tool_result',
        status: event.toolEvent?.status ?? 'succeeded',
        title: event.toolEvent?.displayName ?? event.toolEvent?.toolName ?? 'Tool result',
        toolEvent: event.toolEvent ?? null,
        message: event.toolEvent?.errorMessage ?? null,
      };
    case 'delegation_delta':
      return {
        type: 'delegation_delta',
        status: 'streaming',
        title: 'Sub-agent output',
        delta: event.delta ?? null,
        delegationAgentKey: event.delegationAgentKey ?? null,
      };
    case 'handoff':
      return {
        type: 'handoff',
        status: 'succeeded',
        title: 'Handoff completed',
        replyText: event.replyText ?? null,
        handoffReason: event.handoffReason ?? null,
        delegationAgentKey: event.delegationAgentKey ?? null,
      };
    case 'completed':
      return {
        type: 'reply_completed',
        status: 'succeeded',
        title: 'Reply completed',
        replyText: event.replyText ?? null,
      };
    case 'error':
      return {
        type: 'error',
        status: event.status ?? 'failed',
        title: 'Agent runtime error',
        message: event.errorMessage ?? null,
      };
    default:
      return null;
  }
}

export function buildHistory(
  session: { messages: Array<{ role: string; content: string }> },
): AgentChatMessageInput[] {
  return session.messages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .map((message) => ({
      role: message.role as 'user' | 'assistant',
      content: message.content,
    }));
}

export function findLatestTraceMessageId(
  session: { messages: Array<{ id: string; trace?: unknown }> },
) {
  return [...session.messages].reverse().find((message) => message.trace)?.id ?? null;
}

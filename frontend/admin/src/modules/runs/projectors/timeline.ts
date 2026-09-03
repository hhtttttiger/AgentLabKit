/** Project raw execution events into a human-readable execution timeline. */
import type { RunEvent, RunTimelineItem } from '../types';

type OperationKind = 'run' | 'agent' | 'llm' | 'tool' | 'retrieval' | 'workflow' | null;
type Projection = {
  kind: RunTimelineItem['type'];
  phase: 'start' | 'end' | 'single';
  operation: OperationKind;
};

// This is the only frontend taxonomy registry. Names are the serialized
// RuntimeEvent.event_type values from events_v2.py; legacy/guessed aliases are
// intentionally not accepted as semantic events.
const EVENT_PROJECTIONS: Record<string, Projection> = {
  'run.started': { kind: 'run', phase: 'start', operation: 'run' },
  'run.completed': { kind: 'run', phase: 'end', operation: 'run' },
  'run.failed': { kind: 'error', phase: 'end', operation: 'run' },
  'run.cancelled': { kind: 'error', phase: 'end', operation: 'run' },
  'agent.started': { kind: 'note', phase: 'start', operation: 'agent' },
  'agent.completed': { kind: 'note', phase: 'end', operation: 'agent' },
  'agent.turn_started': { kind: 'note', phase: 'start', operation: 'agent' },
  'agent.turn_completed': { kind: 'note', phase: 'end', operation: 'agent' },
  'llm.call_started': { kind: 'llm', phase: 'start', operation: 'llm' },
  'llm.call_completed': { kind: 'llm', phase: 'end', operation: 'llm' },
  'llm.call_failed': { kind: 'error', phase: 'end', operation: 'llm' },
  'tool.call_started': { kind: 'tool', phase: 'start', operation: 'tool' },
  'tool.call_completed': { kind: 'tool', phase: 'end', operation: 'tool' },
  'tool.call_failed': { kind: 'error', phase: 'end', operation: 'tool' },
  'retrieval.started': { kind: 'note', phase: 'start', operation: 'retrieval' },
  'retrieval.completed': { kind: 'note', phase: 'end', operation: 'retrieval' },
  'retrieval.failed': { kind: 'error', phase: 'end', operation: 'retrieval' },
  'guardrail.evaluated': { kind: 'note', phase: 'single', operation: null },
  'guardrail.blocked': { kind: 'note', phase: 'single', operation: null },
  'handoff.started': { kind: 'note', phase: 'single', operation: 'agent' },
  'handoff.completed': { kind: 'note', phase: 'single', operation: 'agent' },
  'delegation.started': { kind: 'note', phase: 'single', operation: 'agent' },
  'delegation.completed': { kind: 'note', phase: 'single', operation: 'agent' },

  // Legacy serializer names are retained only because the runtime still emits
  // them on its compatibility path. They map to the same semantics above.
  run_start: { kind: 'run', phase: 'start', operation: 'run' },
  run_complete: { kind: 'run', phase: 'end', operation: 'run' },
  llm_started: { kind: 'llm', phase: 'start', operation: 'llm' },
  llm_completed: { kind: 'llm', phase: 'end', operation: 'llm' },
  llm_failed: { kind: 'error', phase: 'end', operation: 'llm' },
  tool_started: { kind: 'tool', phase: 'start', operation: 'tool' },
  tool_completed: { kind: 'tool', phase: 'end', operation: 'tool' },
  tool_failed: { kind: 'error', phase: 'end', operation: 'tool' },
  llm_call: { kind: 'llm', phase: 'single', operation: null },
  model_response: { kind: 'llm', phase: 'single', operation: null },
  completion: { kind: 'llm', phase: 'single', operation: null },
  tool_call: { kind: 'tool', phase: 'single', operation: null },
  function_call: { kind: 'tool', phase: 'single', operation: null },
  error: { kind: 'error', phase: 'single', operation: null },
  exception: { kind: 'error', phase: 'single', operation: null },
};

function sequence(event: RunEvent): number { return event.sequence ?? Number.MAX_SAFE_INTEGER; }
function projection(event: RunEvent): Projection {
  return EVENT_PROJECTIONS[event.type] ?? { kind: 'note', phase: 'single', operation: null };
}

function operationKind(event: RunEvent): OperationKind {
  return projection(event).operation;
}

/** Correlation alone is insufficient: both events must describe one operation kind. */
export function canPair(start: RunEvent, end: RunEvent): boolean {
  const startSpec = projection(start);
  const endSpec = projection(end);
  return Boolean(
    start.spanId && end.spanId && start.spanId === end.spanId &&
    startSpec.phase === 'start' && endSpec.phase === 'end' &&
    operationKind(start) !== null && operationKind(start) === operationKind(end),
  );
}

function title(event: RunEvent): string {
  const data = { ...event.metadata, ...event.payload };
  const value = data.name ?? data.title ?? data.toolName ?? data.tool_name;
  if (typeof value === 'string' && value) return value;
  return event.type.replace(/[_.-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function status(event: RunEvent, kind: RunTimelineItem['type']): string {
  const value = event.payload.status ?? event.metadata.status;
  if (typeof value === 'string') return value;
  if (event.type === 'run.cancelled') return 'cancelled';
  if (event.type === 'guardrail.blocked') return 'blocked';
  if (kind === 'error' || event.type.endsWith('.failed') || event.type.endsWith('_failed')) {
    return event.type === 'error' || event.type === 'exception' ? 'error' : 'failed';
  }
  return 'ok';
}

function duration(start: RunEvent, end: RunEvent): number | null {
  if (!start.timestamp || !end.timestamp) return null;
  const value = new Date(end.timestamp).getTime() - new Date(start.timestamp).getTime();
  return Number.isFinite(value) && value >= 0 ? value : null;
}

function item(event: RunEvent, kind = projection(event).kind, extra: Partial<RunTimelineItem> = {}): RunTimelineItem {
  return {
    id: event.id || `event-${Math.max(0, sequence(event) - 1)}`,
    type: kind,
    title: title(event),
    status: status(event, kind),
    durationMs: typeof event.payload.durationMs === 'number' ? event.payload.durationMs :
      typeof event.payload.duration_ms === 'number' ? event.payload.duration_ms : null,
    startedAt: event.timestamp,
    metadata: { sequence: event.sequence, spanId: event.spanId, eventType: event.type, ...event.metadata, ...extra.metadata },
    ...extra,
  };
}

/** Pair start/end events by correlation and semantic kind, including out-of-order input. */
export function projectRunTimeline(events: RunEvent[]): RunTimelineItem[] {
  const ordered = events.slice().sort((a, b) => sequence(a) - sequence(b));
  const starts = new Map<string, RunEvent>();
  for (const event of ordered) {
    if (projection(event).phase === 'start' && event.spanId) starts.set(event.spanId, event);
  }

  const consumed = new Set<string>();
  const result: RunTimelineItem[] = [];
  for (const event of ordered) {
    const spec = projection(event);
    if (spec.phase === 'start' && event.spanId) {
      if (!consumed.has(event.id)) continue;
    }
    if (spec.phase === 'end' && event.spanId) {
      const start = starts.get(event.spanId);
      if (start && canPair(start, event) && !consumed.has(start.id)) {
        consumed.add(start.id);
        consumed.add(event.id);
        // A cancelled run is still a run outcome, not an infrastructure error.
        const kind = spec.operation === 'run' ? 'run' : spec.kind;
        result.push(item(start, kind, {
          durationMs: duration(start, event),
          status: status(event, kind),
          metadata: { completedAt: event.timestamp, endEventType: event.type },
        }));
        continue;
      }
    }
    if (!consumed.has(event.id)) result.push(item(event));
  }

  for (const start of starts.values()) {
    if (!consumed.has(start.id)) {
      const projected = item(start);
      projected.status = 'incomplete';
      result.push(projected);
    }
  }
  return result.sort((a, b) => Number(a.metadata.sequence ?? 0) - Number(b.metadata.sequence ?? 0));
}

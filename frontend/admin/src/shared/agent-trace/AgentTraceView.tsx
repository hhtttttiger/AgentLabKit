import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  ArrowRightLeft,
  Bot,
  Cable,
  Check,
  ChevronDown,
  Clock3,
  Cpu,
  Wrench,
} from 'lucide-react';
import { cn } from '@/shared/lib/cn';
import type {
  AgentExecutionTrace,
  AgentTraceAppliedSkill,
  AgentTraceToolEvent,
} from './contracts';

type AgentTraceViewProps = {
  trace: AgentExecutionTrace | null;
  title?: string;
  description?: string;
  className?: string;
  emptyTitle?: string;
  emptyDescription?: string;
};

type NodeTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger';
type NodeKind = 'context' | 'tool' | 'delegation' | 'handoff' | 'reply' | 'error' | 'note';

type TimelineNode = {
  id: string;
  kind: NodeKind;
  tone: NodeTone;
  title: string;
  status?: string;
  tool?: AgentTraceToolEvent;
  delta?: string;
  replyText?: string;
  message?: string;
  handoffReason?: string;
  delegationAgentKey?: string;
  appliedSkills?: AgentTraceAppliedSkill[];
};

const toneMarker: Record<NodeTone, string> = {
  neutral: 'bg-text-muted/10 text-text-muted ring-text-muted/15',
  primary: 'bg-primary/10 text-primary ring-primary/20',
  success: 'bg-success/10 text-success ring-success/20',
  warning: 'bg-warning/10 text-warning ring-warning/20',
  danger: 'bg-error/10 text-error ring-error/20',
};

const toneDot: Record<NodeTone, string> = {
  neutral: 'bg-text-muted',
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-error',
};

export function AgentTraceView({
  trace,
  title,
  description,
  className,
  emptyTitle,
  emptyDescription,
}: AgentTraceViewProps) {
  const { t } = useTranslation(['common', 'aiChat']);
  const resolvedTitle = title ?? t('aiChat:trace.title');
  const resolvedDescription = description ?? t('aiChat:trace.description');
  const resolvedEmptyTitle = emptyTitle ?? t('aiChat:trace.emptyTitle');
  const resolvedEmptyDescription = emptyDescription ?? t('aiChat:trace.emptyDescription');

  if (!trace) {
    return (
      <section className={cn('flex h-full min-h-0 flex-col', className)}>
        <Header title={resolvedTitle} description={resolvedDescription} />
        <div className="flex min-h-0 flex-1 items-center justify-center px-5 py-6">
          <div className="max-w-sm rounded-[2px] border border-dashed border-border bg-surface-subtle/70 px-6 py-8 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-[2px] bg-primary/10 text-primary">
              <Bot className="h-5 w-5" />
            </div>
            <div className="mt-4 text-sm font-semibold text-text">{resolvedEmptyTitle}</div>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{resolvedEmptyDescription}</p>
          </div>
        </div>
      </section>
    );
  }

  const nodes = buildTimeline(trace);
  const usage = formatUsage(trace);
  const runTone = statusTone(trace.status);

  return (
    <section className={cn('flex h-full min-h-0 flex-col', className)}>
      <header className="border-b border-border bg-surface px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-text">{resolvedTitle}</h2>
          <span className="inline-flex shrink-0 items-center gap-1.5 text-xs font-medium text-text-secondary">
            <span className={cn('h-1.5 w-1.5 rounded-full', toneDot[runTone])} />
            {trace.status}
          </span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-secondary">
          <span className="font-medium text-text">{trace.agentKey}</span>
          <span className="text-text-subtle">v{trace.agentVersion}</span>
          <span className="text-text-subtle">·</span>
          <span>{trace.action}</span>
          {usage !== 'n/a' ? (
            <>
              <span className="text-text-subtle">·</span>
              <span>{usage}</span>
            </>
          ) : null}
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="space-y-4">
          {trace.errorMessage ? (
            <div className="rounded-[2px] bg-error-subtle px-3 py-2 text-xs leading-5 text-error-text">
              {trace.errorCode ? <span className="font-semibold">{trace.errorCode}: </span> : null}
              {trace.errorMessage}
            </div>
          ) : null}

          {trace.appliedSkills.length ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="mr-0.5 text-xs text-text-muted">{t('aiChat:trace.skillsLabel')}</span>
              {trace.appliedSkills.map((skill) => (
                <SkillChip key={`${skill.skillKey}-${skill.order}`} skill={skill} />
              ))}
            </div>
          ) : null}

          {nodes.length ? (
            <ol>
              {nodes.map((node, index) => (
                <TimelineNodeRow key={node.id} node={node} isLast={index === nodes.length - 1} />
              ))}
            </ol>
          ) : (
            <p className="text-sm text-text-muted">{t('aiChat:trace.tools.noResults')}</p>
          )}
        </div>
      </div>

      <RunDetailsFooter trace={trace} />
    </section>
  );
}

function Header({ title, description }: { title: string; description?: string }) {
  return (
    <div className="border-b border-border bg-surface px-5 py-4">
      <div className="text-base font-semibold text-text">{title}</div>
      {description ? <p className="mt-1 text-sm leading-6 text-text-secondary">{description}</p> : null}
    </div>
  );
}

function TimelineNodeRow({ node, isLast }: { node: TimelineNode; isLast: boolean }) {
  const Icon = iconForKind(node.kind);
  return (
    <li className={cn('grid grid-cols-[24px_minmax(0,1fr)] gap-3', isLast ? '' : 'pb-4')}>
      <div className="flex flex-col items-center">
        <span
          className={cn(
            'flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-1 ring-inset',
            toneMarker[node.tone],
          )}
        >
          <Icon className="h-3 w-3" />
        </span>
        {isLast ? null : <span className="w-px grow bg-border" />}
      </div>
      <div className="min-w-0 pt-0.5">
        <div className="truncate text-sm font-semibold text-text">{node.title}</div>
        <NodeMeta node={node} />
        <NodeBody node={node} />
      </div>
    </li>
  );
}

function NodeMeta({ node }: { node: TimelineNode }) {
  const bits: ReactNode[] = [];
  if (node.status) bits.push(<span key="status">{node.status}</span>);
  if (node.tool?.durationMs) {
    bits.push(
      <span key="duration" className="inline-flex items-center gap-1">
        <Clock3 className="h-3 w-3" />
        {formatDuration(node.tool.durationMs)}
      </span>,
    );
  }
  const source = sourceLabel(node.tool?.sourceType);
  if (source) bits.push(<span key="source" className="text-text-subtle">{source}</span>);
  if (node.tool?.sourceRef) bits.push(<span key="ref" className="text-text-subtle">{node.tool.sourceRef}</span>);
  if (node.tool?.toolName && node.tool.toolName !== node.title) {
    bits.push(<span key="name" className="font-mono text-text-subtle">{node.tool.toolName}</span>);
  }
  if (node.delegationAgentKey) {
    bits.push(
      <span key="agent" className="inline-flex items-center gap-1">
        <Cable className="h-3 w-3" />
        {node.delegationAgentKey}
      </span>,
    );
  }
  if (!bits.length) return null;
  return <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-text-muted">{bits}</div>;
}

function NodeBody({ node }: { node: TimelineNode }) {
  const { t } = useTranslation(['common', 'aiChat']);
  switch (node.kind) {
    case 'tool':
      if (node.tool) return <ToolPayload tool={node.tool} extraMessage={node.message} />;
      return node.message ? <p className="mt-1.5 text-xs leading-5 text-error-text">{node.message}</p> : null;
    case 'reply':
      return node.replyText ? <ProseText text={node.replyText} tone="primary" /> : null;
    case 'delegation':
      return node.delta ? <ProseText text={node.delta} tone="muted" /> : null;
    case 'handoff':
      return (
        <>
          {node.handoffReason ? (
            <p className="mt-1.5 text-xs leading-5 text-text-secondary">
              {t('aiChat:trace.reasonLabel')}: {node.handoffReason}
            </p>
          ) : null}
          {node.replyText ? <ProseText text={node.replyText} tone="muted" /> : null}
        </>
      );
    case 'context':
      return node.appliedSkills?.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {node.appliedSkills.map((skill) => (
            <SkillChip key={`${skill.skillKey}-${skill.order}`} skill={skill} />
          ))}
        </div>
      ) : null;
    case 'error':
      return node.message ? <p className="mt-1.5 text-xs leading-5 text-error-text">{node.message}</p> : null;
    default:
      return node.message ? <p className="mt-1.5 text-xs leading-5 text-text-secondary">{node.message}</p> : null;
  }
}

function ProseText({ text, tone }: { text: string; tone: 'primary' | 'muted' }) {
  return (
    <div
      className={cn(
        'mt-1.5 whitespace-pre-wrap break-words text-sm leading-6',
        tone === 'primary' ? 'text-text' : 'text-text-secondary',
      )}
    >
      {text}
    </div>
  );
}

function ToolPayload({ tool, extraMessage }: { tool: AgentTraceToolEvent; extraMessage?: string }) {
  const { t } = useTranslation(['common', 'aiChat']);
  const [open, setOpen] = useState(false);
  const hasArgs = hasObjectKeys(tool.arguments);
  const hasOutput = Boolean(tool.outputText);
  const expandable = hasArgs || hasOutput;
  const errorMessage = tool.errorMessage ?? extraMessage;

  return (
    <div className="mt-2 space-y-2">
      {tool.tags.length ? (
        <div className="flex flex-wrap gap-1.5">
          {tool.tags.map((tag) => (
            <span key={tag} className="rounded-full bg-background-subtle px-2 py-0.5 text-[11px] text-text-secondary">
              {tag}
            </span>
          ))}
        </div>
      ) : null}
      {errorMessage ? <p className="text-xs leading-5 text-error-text">{errorMessage}</p> : null}
      {expandable ? (
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="inline-flex items-center gap-1 text-xs font-medium text-text-secondary transition hover:text-text"
            aria-expanded={open}
          >
            <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open ? 'rotate-180' : '')} />
            {open ? t('aiChat:trace.toolCollapse') : t('aiChat:trace.toolExpand')}
          </button>
          <div className={cn('space-y-2', open ? '' : 'hidden')}>
            {hasArgs ? <CodeBlock label="Arguments" value={JSON.stringify(tool.arguments, null, 2)} /> : null}
            {hasOutput && tool.outputText ? <CodeBlock label="Output" value={tool.outputText} /> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function CodeBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">{label}</div>
      <pre
        className="max-h-[220px] overflow-auto rounded-[2px] border border-border/20 bg-[#0f1f33] px-3 py-3 font-mono text-xs leading-6 whitespace-pre-wrap break-all text-[#e8f1ff] dark:bg-[#0a1525]"
        style={{ scrollbarGutter: 'stable' }}
      >
        {value}
      </pre>
    </div>
  );
}

function SkillChip({ skill }: { skill: AgentTraceAppliedSkill }) {
  return (
    <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
      {skill.displayName}
    </span>
  );
}

function RunDetailsFooter({ trace }: { trace: AgentExecutionTrace }) {
  const { t } = useTranslation(['common', 'aiChat']);
  const [open, setOpen] = useState(false);
  const rows: Array<[string, string]> = [
    ['Run', trace.runId],
    ['Trace', trace.traceId],
    ['Session', trace.sessionId],
  ];
  return (
    <div className="border-t border-border bg-surface px-5 py-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-2 text-xs text-text-secondary transition hover:text-text"
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-1.5">
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open ? 'rotate-180' : '')} />
          {t('aiChat:trace.runDetails')}
        </span>
        <span className="font-mono text-text-muted">{shortenId(trace.runId)}</span>
      </button>
      {open ? (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-xs">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-text-muted">{label}</dt>
              <dd className="break-all font-mono text-text">{value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

function buildTimeline(trace: AgentExecutionTrace): TimelineNode[] {
  const nodes: TimelineNode[] = [];
  const pendingByTool = new Map<string, number[]>();

  const pushToolCall = (tool: AgentTraceToolEvent | null | undefined, title: string) => {
    const index = nodes.length;
    nodes.push({
      id: `tool-${index}`,
      kind: 'tool',
      tone: 'primary',
      title,
      status: 'running',
      tool: tool ?? undefined,
    });
    if (tool?.toolName) {
      const queue = pendingByTool.get(tool.toolName) ?? [];
      queue.push(index);
      pendingByTool.set(tool.toolName, queue);
    }
  };

  const resolveToolResult = (tool: AgentTraceToolEvent, status: string) => {
    const queue = pendingByTool.get(tool.toolName);
    if (queue && queue.length) {
      const index = queue.shift()!;
      const node = nodes[index];
      node.tool = tool;
      node.status = status;
      node.tone = statusTone(status);
      if (status === 'failed' || status === 'error') {
        node.message = tool.errorMessage ?? undefined;
      }
      if (!queue.length) pendingByTool.delete(tool.toolName);
      return true;
    }
    return false;
  };

  for (const step of trace.steps) {
    switch (step.type) {
      case 'context':
        nodes.push({
          id: `ctx-${nodes.length}`,
          kind: 'context',
          tone: 'success',
          title: step.title,
          appliedSkills: step.appliedSkills ?? undefined,
        });
        break;
      case 'tool_call':
        pushToolCall(step.toolEvent, step.title || step.toolEvent?.toolName || 'Tool call');
        break;
      case 'tool_result': {
        const status = step.toolEvent?.status ?? step.status ?? 'succeeded';
        const resolved = step.toolEvent ? resolveToolResult(step.toolEvent, status) : false;
        if (!resolved) {
          nodes.push({
            id: `tool-${nodes.length}`,
            kind: 'tool',
            tone: statusTone(status),
            title: step.title || step.toolEvent?.toolName || 'Tool result',
            status,
            tool: step.toolEvent ?? undefined,
            message: step.message ?? undefined,
          });
        }
        break;
      }
      case 'delegation_delta':
        nodes.push({
          id: `del-${nodes.length}`,
          kind: 'delegation',
          tone: 'warning',
          title: step.title,
          status: 'streaming',
          delta: step.delta ?? undefined,
          delegationAgentKey: step.delegationAgentKey ?? undefined,
        });
        break;
      case 'handoff':
        nodes.push({
          id: `hnd-${nodes.length}`,
          kind: 'handoff',
          tone: 'warning',
          title: step.title,
          status: step.status,
          replyText: step.replyText ?? undefined,
          handoffReason: step.handoffReason ?? undefined,
          delegationAgentKey: step.delegationAgentKey ?? undefined,
        });
        break;
      case 'reply_completed':
        nodes.push({
          id: `rpl-${nodes.length}`,
          kind: 'reply',
          tone: 'success',
          title: step.title,
          status: step.status,
          replyText: step.replyText ?? undefined,
        });
        break;
      case 'error':
        nodes.push({
          id: `err-${nodes.length}`,
          kind: 'error',
          tone: 'danger',
          title: step.title,
          status: step.status,
          message: step.message ?? undefined,
        });
        break;
      default:
        nodes.push({
          id: `step-${nodes.length}`,
          kind: 'note',
          tone: 'neutral',
          title: step.title,
          status: step.status,
          message: step.message ?? undefined,
        });
    }
  }

  // Fallback for traces that carry toolEvents but no tool steps (e.g. legacy / persisted traces).
  if (!nodes.some((node) => node.kind === 'tool') && trace.toolEvents.length) {
    trace.toolEvents.forEach((tool) => {
      nodes.push({
        id: `tool-${nodes.length}`,
        kind: 'tool',
        tone: statusTone(tool.status),
        title: tool.displayName ?? tool.toolName,
        status: tool.status,
        tool,
      });
    });
  }

  return nodes;
}

function statusTone(status?: string | null): NodeTone {
  const value = (status ?? '').toLowerCase();
  if (value === 'failed' || value === 'error') return 'danger';
  if (value === 'succeeded' || value === 'success' || value === 'completed') return 'success';
  if (value === 'running' || value === 'streaming' || value === 'ready') return 'primary';
  if (value === 'timeout') return 'warning';
  return 'neutral';
}

function iconForKind(kind: NodeKind) {
  switch (kind) {
    case 'tool':
      return Wrench;
    case 'delegation':
      return Cable;
    case 'handoff':
      return ArrowRightLeft;
    case 'reply':
      return Check;
    case 'error':
      return AlertTriangle;
    case 'context':
    default:
      return Cpu;
  }
}

function sourceLabel(sourceType?: string | null) {
  if (sourceType === 'mcp') return 'MCP';
  if (sourceType === 'http_external') return 'HTTP';
  if (sourceType === 'delegate') return 'Delegate';
  if (sourceType) return 'Builtin';
  return null;
}

function shortenId(value: string) {
  return value.length > 10 ? `${value.slice(0, 10)}…` : value;
}

function formatUsage(trace: AgentExecutionTrace) {
  if (!trace.usage) {
    return 'n/a';
  }
  const parts = [
    trace.usage.totalTokens != null ? `${trace.usage.totalTokens} tokens` : null,
    trace.usage.audioDurationMs != null ? formatDuration(trace.usage.audioDurationMs) : null,
  ].filter(Boolean);
  return parts.join(' · ') || 'n/a';
}

function formatDuration(durationMs: number) {
  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }
  return `${(durationMs / 1000).toFixed(2)}s`;
}

function hasObjectKeys(value: Record<string, unknown>) {
  return Object.keys(value).length > 0;
}

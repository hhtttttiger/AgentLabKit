export type AgentTraceUsage = {
  inputTokens?: number | null;
  outputTokens?: number | null;
  totalTokens?: number | null;
  audioDurationMs?: number | null;
};

export type AgentTraceAppliedSkill = {
  skillKey: string;
  displayName: string;
  order: number;
  config: Record<string, unknown>;
};

export type AgentTraceToolEvent = {
  toolName: string;
  status: string;
  arguments: Record<string, unknown>;
  outputText?: string | null;
  errorMessage?: string | null;
  displayName?: string | null;
  sourceType?: string | null;
  sourceRef?: string | null;
  tags: string[];
  durationMs?: number | null;
};

export type AgentTraceStep = {
  type: string;
  status: string;
  title: string;
  delta?: string | null;
  replyText?: string | null;
  message?: string | null;
  handoffReason?: string | null;
  delegationAgentKey?: string | null;
  toolEvent?: AgentTraceToolEvent | null;
  appliedSkills?: AgentTraceAppliedSkill[] | null;
};

export type AgentExecutionTrace = {
  runId: string;
  sessionId: string;
  traceId: string;
  agentKey: string;
  agentVersion: number;
  status: string;
  action: string;
  replyText?: string | null;
  handoffReason?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  appliedSkills: AgentTraceAppliedSkill[];
  toolEvents: AgentTraceToolEvent[];
  steps: AgentTraceStep[];
  usage?: AgentTraceUsage | null;
  startedAtUtc?: string | null;
  completedAtUtc?: string | null;
};

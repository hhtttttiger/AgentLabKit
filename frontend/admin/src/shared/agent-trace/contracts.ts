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

export type AgentTraceRetrievalResult = {
  knowledgeBaseId: string | null;
  documentId: string | null;
  segmentId: string | null;
  score: number | null;
  title: string | null;
  source: string | null;
  contentPreview: string | null;
};

export type AgentTraceRetrievalEvent = {
  status: 'succeeded' | 'failed';
  query: string | null;
  source: string | null;
  knowledgeBaseIds: string[];
  topK: number | null;
  searchMode: string | null;
  resultCount: number | null;
  durationMs: number | null;
  results: AgentTraceRetrievalResult[];
  errorMessage: string | null;
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
  retrievalEvent?: AgentTraceRetrievalEvent | null;
  appliedSkills?: AgentTraceAppliedSkill[] | null;
};

export type AgentExecutionTrace = {
  runId: string;
  sessionId: string | null;
  traceId: string;
  agentKey: string | null;
  agentVersion: number | null;
  status: string;
  action: string | null;
  replyText?: string | null;
  handoffReason?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  appliedSkills: AgentTraceAppliedSkill[];
  toolEvents: AgentTraceToolEvent[];
  retrievalEvents: AgentTraceRetrievalEvent[];
  steps: AgentTraceStep[];
  usage?: AgentTraceUsage | null;
  startedAtUtc?: string | null;
  completedAtUtc?: string | null;
};

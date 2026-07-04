/**
 * AI Chat Module - Type Definitions
 */

import type { AgentExecutionTrace } from '@/shared/agent-trace/contracts';

// ---------------------------------------------------------------------------
// Message Types
// ---------------------------------------------------------------------------

export type MessageRole = 'user' | 'assistant' | 'system';

export type MessageStatus = 'sending' | 'sent' | 'failed';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  status?: MessageStatus;
  error?: string;
  trace?: AgentExecutionTrace | null;
}

// ---------------------------------------------------------------------------
// Session Types
// ---------------------------------------------------------------------------

export type ModelType = 'agent' | 'model';

export interface ChatSession {
  id: number | string; // server-assigned snowflake (number) or legacy localStorage ID (string)
  title: string;
  modelType: ModelType;
  modelId: string; // agentKey or modelId
  cardId?: string; // actual cardId used (for agent mode, deprecated)
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// ── Server DTOs (camelCase output from backend CamelModel) ────────────

export interface ChatSessionDto {
  id: number | string; // snowflake IDs >2^53 arrive as strings from SnowflakeJSONResponse
  userId: string;
  title: string;
  modelType: string;
  modelId: string;
  messageCount: number;
  createdAtUtc: string;
  updatedAtUtc: string;
}

export interface ChatMessageDto {
  id: number | string;
  sessionId: number | string;
  role: string;
  content: string;
  status: string;
  errorMessage?: string | null;
  traceJson?: Record<string, unknown> | null;
  createdAtUtc: string;
}

export interface SaveTurnRequest {
  userMessage: SaveMessageDto;
  assistantMessage: SaveMessageDto;
}

export interface SaveMessageDto {
  role: string;
  content: string;
  status?: string;
  errorMessage?: string | null;
  traceJson?: Record<string, unknown> | null;
}

export interface SaveTurnResponse {
  userMessageId: number | string;
  assistantMessageId: number | string;
}

// ── Converter helpers ────────────────────────────────────────────────

export function dtoToSession(dto: ChatSessionDto): ChatSession {
  return {
    // Snowflake IDs exceed JS Number.MAX_SAFE_INTEGER; backend serializes them
    // as strings via SnowflakeJSONResponse.  Preserve the string so we can
    // safely round-trip to the API.
    id: typeof dto.id === 'number' ? String(dto.id) : dto.id,
    title: dto.title,
    modelType: dto.modelType as ModelType,
    modelId: dto.modelId,
    messages: [],
    createdAt: new Date(dto.createdAtUtc).getTime(),
    updatedAt: new Date(dto.updatedAtUtc).getTime(),
  };
}

/** True when the id was assigned by the server (snowflake, stored in DB). */
export function isServerSessionId(id: number | string): id is number | string {
  if (typeof id === 'number') return true;
  // Snowflake IDs arrive as numeric strings from JSON (JS precision limit)
  return /^\d{16,}$/.test(id);
}

export function dtoToMessage(dto: ChatMessageDto): ChatMessage {
  return {
    id: String(dto.id),
    role: dto.role as MessageRole,
    content: dto.content,
    timestamp: new Date(dto.createdAtUtc).getTime(),
    status: dto.status as MessageStatus,
    error: dto.errorMessage ?? undefined,
    trace: dto.traceJson as ChatMessage['trace'],
  };
}

export interface CreateSessionOptions {
  modelType: ModelType;
  modelId: string;
  title?: string;
}

// ---------------------------------------------------------------------------
// API Request/Response Types
// ---------------------------------------------------------------------------

export interface ChatRequest {
  message: string;
  systemPrompt?: string;
  sessionId?: string;
  history?: AgentChatMessageInput[];
}

export interface AgentChatMessageInput {
  role: MessageRole;
  content: string;
  name?: string;
  metadata?: Record<string, string>;
}

export interface StreamChunk {
  content: string;
  done: boolean;
}

// Response from backend AI invoke endpoint
export interface AiInvokeResultDto {
  success: boolean;
  modelId: string;
  capability: string;
  requestId: string;
  attemptCount: number;
  finalInstanceId?: string;
  error?: string;
  usage?: AiInvokeUsageDto;
  payload?: AiInvokePayload;
}

export interface AiInvokeUsageDto {
  inputTokens?: number;
  outputTokens?: number;
  estimatedCost?: number;
}

export interface AiInvokePayload {
  content?: string;
  text?: string;
  audioBase64?: string;
  voice?: string;
  language?: string;
  model?: string;
  imageUrl?: string;
  vector?: number[];
  toolName?: string;
  arguments?: string;
  result?: string;
  sessionId?: string;
  clientSecret?: string;
  expiresAtUtc?: string;
}

// ---------------------------------------------------------------------------
// Stream Callback Types
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
  onChunk: (chunk: StreamChunk) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
}

export type AgentStreamEventType =
  | 'context'
  | 'reply_delta'
  | 'completed'
  | 'tool_call'
  | 'tool_result'
  | 'delegation_delta'
  | 'handoff'
  | 'error';

export interface AgentStreamEvent {
  type: AgentStreamEventType;
  runId: string;
  sessionId: string;
  traceId: string;
  agentKey?: string | null;
  agentVersion?: number | null;
  status?: string | null;
  action?: string | null;
  delta?: string | null;
  replyText?: string | null;
  message?: string | null;
  handoffReason?: string | null;
  delegationAgentKey?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  appliedSkills?: AgentExecutionTrace['appliedSkills'] | null;
  toolEvent?: AgentExecutionTrace['toolEvents'][number] | null;
  usage?: AgentExecutionTrace['usage'] | null;
}

export interface AgentStreamCallbacks {
  onEvent: (event: AgentStreamEvent) => void;
  onError: (error: Error) => void;
  onComplete: () => void;
}

// ---------------------------------------------------------------------------
// Chat History Storage Types
// ---------------------------------------------------------------------------

export interface ChatHistoryStorage {
  loadSessions(): ChatSession[];
  saveSession(session: ChatSession): void;
  deleteSession(id: string): void;
  getSession(id: string): ChatSession | undefined;
  clearAll(): void;
}

// ---------------------------------------------------------------------------
// Model Selection Types
// ---------------------------------------------------------------------------

export interface ModelOption {
  id: string;
  name: string;
  description?: string;
  type: ModelType;
  cardId?: string; // For agents, the associated cardId (deprecated, use modelId)
}

export interface AgentOption extends ModelOption {
  type: 'agent';
  publishedVersionNumber: number;
}

export interface ModelCardOption extends ModelOption {
  type: 'model';
}

# AI Chat Page Optimization — Design Doc

**Date:** 2026-06-27
**Status:** approved

---

## Summary

Three-layer optimization of the AI chat page: server-side session persistence (new DB tables + REST API), frontend performance (streaming throttle, React.memo, component decomposition), and UX polish (Markdown rendering, message actions, empty states).

---

## L1 — Backend: Session Persistence

### Problem

Chat sessions are stored entirely in localStorage. This is synchronous, size-limited (~5MB), lost on browser clear/device switch, and silently truncated at 50 sessions / 500 messages per session. Every API call already passes a `SessionId`, but the backend doesn't store sessions or messages — the frontend ships the full `History` array on every request.

### Database

**New tables:**

#### `chat_sessions`

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT PK | Snowflake |
| user_id | VARCHAR(128) NOT NULL | Indexed |
| title | VARCHAR(512) NOT NULL | |
| model_type | VARCHAR(16) NOT NULL | `'agent'` \| `'model'` |
| model_id | VARCHAR(128) NOT NULL | agent_key or model_key |
| message_count | INT DEFAULT 0 | Denormalized counter |
| created_at_utc | TIMESTAMPTZ | |
| updated_at_utc | TIMESTAMPTZ | |

Index: `(user_id, updated_at_utc DESC)` for sorted listing.

#### `chat_messages`

| Column | Type | Notes |
|--------|------|-------|
| id | BIGINT PK | Snowflake |
| session_id | BIGINT NOT NULL FK → chat_sessions | CASCADE delete |
| role | VARCHAR(16) NOT NULL | `'user'` \| `'assistant'` \| `'system'` |
| content | TEXT NOT NULL | |
| status | VARCHAR(16) DEFAULT `'sent'` | `'sending'` \| `'sent'` \| `'failed'` |
| error_message | TEXT | |
| trace_json | JSONB | AgentExecutionTrace (agent mode only) |
| created_at_utc | TIMESTAMPTZ | |

Index: `(session_id, created_at_utc)` for cursor-based pagination.

### API Endpoints

All under `/api/chat/`, all require authentication.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sessions` | List sessions for current user. Query: `page`, `pageSize`, sorted by `updated_at_utc DESC`. |
| `POST` | `/sessions` | Create session. Body: `{ title, model_type, model_id }`. Returns session with server-assigned snowflake ID. |
| `GET` | `/sessions/{id}` | Get session detail (metadata only, no messages). |
| `PATCH` | `/sessions/{id}` | Update session fields (title, etc.). |
| `DELETE` | `/sessions/{id}` | Delete session + cascade all messages. |
| `GET` | `/sessions/{id}/messages` | Get messages. Query: `cursor` (message id), `limit`. Cursor-based pagination for stable streaming. |
| `POST` | `/sessions/{id}/messages/save-turn` | Save a complete turn after streaming finishes. Body: `{ user_message: {...}, assistant_message: {...} }`. Atomic — both messages + trace in one transaction. Increments session `message_count`. |

### Data Flow: Streaming → Persistence

1. **Page load**: `GET /sessions` → populate session list sidebar. If empty, user creates new via `POST /sessions`.
2. **Select session**: `GET /sessions/{id}/messages` → populate message panel. Cursor-based for large sessions.
3. **Send message**: Frontend creates user message + placeholder assistant message in local state (immediate UI). Streaming proceeds through existing `ai_invoke` SSE endpoints — unchanged.
4. **During streaming**: Messages update in-memory via `requestAnimationFrame`-throttled setState. No API calls, no localStorage writes.
5. **Streaming complete**: `POST /sessions/{id}/messages/save-turn` with the finalized user message + assistant message + trace. Backend inserts both rows in one transaction.
6. **Switch session**: Save any pending state, fetch next session's messages.
7. **Offline/degraded**: If `save_turn` API fails, fall back to localStorage. On next page load, detect unsaved turns and retry.

### Module Structure

```
backend/src/modules/chat/
├── __init__.py
├── models.py              # ChatSessionOrm, ChatMessageOrm
├── schemas.py             # Pydantic request/response models
├── session_service.py     # ChatSessionService (all business logic)
├── dependencies.py        # get_session_service → FastAPI Depends
└── router.py              # Thin routes — param extraction + call service + return response
```

### Key Behaviors

- **Session creation**: Frontend calls `POST /sessions` before first message to get a server-side session ID. This ID replaces the current `session-{ts}-{rand}` local-only ID.
- **Message persistence**: Happens server-side. The `save_turn` endpoint receives the complete turn after streaming finishes. Streaming itself continues through the existing `ai_invoke` SSE endpoints unchanged — only the "save" step moves to the backend.
- **Backward compatibility**: Legacy localStorage sessions continue to work. On first page load, if localStorage has sessions not present on the server, offer a one-time migration.
- **AgentExecutionAudit**: Unchanged. Continues as an independent audit/observability log. No coupling with chat persistence.

---

## L2 — Frontend: Performance

### Problem

During streaming, every SSE event triggers: `setState` → full component tree re-render → `localStorage.setItem` (full read + JSON.parse + stringify). On agent mode with heavy tool calls, this can hit 50+ writes per second. The 417-line `AiChatPage.tsx` mixes session CRUD, streaming orchestration, model selection, and trace panel control.

### Component Decomposition

```
modules/ai-chat/
├── hooks/
│   ├── useChatSession.ts     # Session CRUD — list from API, create, delete, select
│   ├── useChatStream.ts      # sendMessage + streaming state (unified agent/card)
│   └── useTracePanel.ts      # Trace selection / toggle
├── pages/
│   └── AiChatPage.tsx        # ~100 lines — composes hooks, renders layout
```

**`useChatSession`**: Owns `sessions[]`, `currentSession`, fetch from API on mount, localStorage as cache fallback.

**`useChatStream`**: Owns `isLoading`, `abortFn`, `sendMessage()`. Internally branches on `session.modelType` to call `streamAgentChatMessage` or `streamCardChatMessage`. Streaming updates are batched with `requestAnimationFrame`. Returns `abort()` for stop button.

**`useTracePanel`**: Owns `selectedTraceMessageId`, `toggleTrace()`. Small, self-contained.

### Rendering Optimizations

- **`ChatMessageBubble`** wrapped in `React.memo` with a custom comparator: re-renders only when `message.content`, `message.status`, `message.trace`, or `selected` changes.
- **Scroll-to-bottom**: uses `scrollIntoView({ behavior: 'smooth' })` on the last message element only, rather than setting `scrollTop = scrollHeight` on every messages change.
- **Accessibility**: message list container gets `role="log"` + `aria-live="polite"` so screen readers announce new messages during streaming.

### localStorage Degradation

- **Before**: Primary storage. Written on every state update during streaming.
- **After**: Cache layer. Written once per session change (debounced 1s). API is the source of truth. On page load: API → populate state → write localStorage snapshot. If API fails: read localStorage snapshot for offline resilience.

---

## L3 — Frontend: UX Polish

### Markdown Rendering

Introduce `react-markdown` + `remark-gfm` (tables, strikethrough, task lists) + `rehype-highlight` (syntax highlighting).

- **Streaming**: During streaming, render with `react-markdown` as content accumulates. `react-markdown` handles partial markdown gracefully.
- **Code blocks**: Custom `code` component. `<pre>` blocks get a language label (top-left) and a copy button (top-right). Copy feedback: clipboard icon → check icon for 2s.
- **Links**: Open in `target="_blank"` with `rel="noopener noreferrer"`.
- **Whitelist**: Only standard Markdown elements. No raw HTML passthrough.

### Message Actions

Hover on assistant message bubbles shows an action bar:

```
[📋 Copy] [🔄 Regenerate]
```

- **Copy**: Copies raw text content to clipboard. Brief "Copied" toast.
- **Regenerate**: Deletes the assistant message from the session, then re-sends the preceding user message. Uses the same `sendMessage` path.

### Send → Stop Button

When `isLoading` is true, the send button (arrow-up icon) transforms into a stop button (square icon). Clicking calls `abort()` which triggers the AbortController.

### Empty State

Replace plain text with an actionable prompt:

- Model selector dropdown embedded in the empty state area
- Text input box directly below
- Visual AI icon (reuse the existing "AI" badge)

### Session Switch Transition

When switching sessions, show `<Skeleton>` placeholders (reuse `shared/ui/Skeleton.tsx`) while messages load. Avoids the jarring instant-content-swap.

---

## Files Changed

### Backend (new)

| File | Action |
|------|--------|
| `modules/chat/models.py` | New — ChatSessionOrm, ChatMessageOrm |
| `modules/chat/schemas.py` | New — request/response Pydantic models |
| `modules/chat/session_service.py` | New — ChatSessionService |
| `modules/chat/dependencies.py` | New — get_session_service Depends |
| `modules/chat/router.py` | Rewrite — replace 501 stubs with implemented endpoints |
| `alembic/versions/0009_chat_sessions.py` | New — migration |

### Frontend

| File | Action |
|------|--------|
| `ai-chat/hooks/useChatSession.ts` | New |
| `ai-chat/hooks/useChatStream.ts` | New |
| `ai-chat/hooks/useTracePanel.ts` | New |
| `ai-chat/components/ChatMessageBubble.tsx` | Extracted from ChatMessagePanel, memo, Markdown, actions |
| `ai-chat/components/ChatMessagePanel.tsx` | Simplified — list rendering + empty state + skeleton |
| `ai-chat/components/ChatInputArea.tsx` | Modified — send/stop button toggle |
| `ai-chat/pages/AiChatPage.tsx` | Rewritten — hook composition, ~100 lines |
| `ai-chat/api.ts` | Modified — add session CRUD API functions |
| `ai-chat/lib/chat-history.ts` | Modified — localStorage degraded to cache layer |
| `ai-chat/lib/contracts.ts` | Modified — types aligned with backend schemas |
| `shared/ui/Skeleton.tsx` | May need minor adjustments for chat-specific skeleton shapes |
| `package.json` | Add `react-markdown`, `remark-gfm`, `rehype-highlight` |

---

## Out of Scope

- Voice input (Mic button remains placeholder)
- File/image attachment (Plus button remains placeholder)
- Tool settings panel (SlidersHorizontal button remains placeholder)
- Message editing (edit-in-place for sent messages)
- Conversation branching / forking
- Full-text search across conversations
- Multi-user conversation sharing

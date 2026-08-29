# AgentLabKit Execution Model v2 重构计划

## 进度追踪

| Phase | 状态 | 完成日期 | 备注 |
|-------|------|----------|------|
| Phase 0: 冻结现状 | ✅ 完成 | 2026-08-29 | EventBus 15 tests, Trace 构建 14 tests, Evaluation Runner 10 tests, Cost contracts 14 tests |
| Phase 1: Runtime Event v2 | ✅ 完成 | 2026-08-29 | 23 事件类型, 70 tests, Dual Emit in run_agent_loop |
| Phase 2: AgentRun | ⬜ 待开始 | | |
| Phase 3: Observability Projection | ⬜ 待开始 | | |
| Phase 4: Cost Projection | ⬜ 待开始 | | |
| Phase 5: Evaluation Core v2 | ⬜ 待开始 | | |
| Phase 6: Agent Native Evaluators | ⬜ 待开始 | | |
| Phase 7: Dataset Regression | ⬜ 待开始 | | |
| Phase 8: Compare | ⬜ 待开始 | | |
| Phase 9: Replay MVP | ⬜ 待开始 | | |
| Phase 10: CLI + CI | ⬜ 待开始 | | |

---

## 1. 重构目标

本次重构的核心目标：

> 将 AgentLabKit 从多个平台模块分别理解 Agent 执行过程，重构为统一的 Run-Centric Execution Model。

最终形成统一的数据流：

```text
Agent Runtime
      │
      ▼
 Semantic Runtime Events
      │
      ▼
   AgentRun
      │
      ├──────────► Trace / Observability
      │
      ├──────────► Cost Analysis
      │
      ├──────────► Evaluation
      │
      ├──────────► Replay
      │
      └──────────► Analytics
```

核心原则：

```text
Runtime 是事实生产者

Event 是事实记录

Run 是一次执行的业务边界

Trace 是执行事实的观测投影

Evaluation / Cost / Replay 是事实消费者
```

不允许 Evaluation、Cost、Observability 各自重新解释一次 Agent 执行。

---

## 2. 本次不解决的问题

避免重构范围无限扩大。

本阶段明确不做：

```text
Production Eval Platform
Human Annotation Platform
完整 Experiment Dashboard
Failure Clustering / RCA
Time Travel Debugger
任意 Span Fork
分布式 Eval Worker
多租户 Eval 平台
复杂 Alerting
```

这些能力必须能够由新模型扩展出来，但本次不实现。

---

## 3. 当前架构问题

当前大致结构：

```text
agent_runtime
    │
    ├── EventBus
    │
    ├── Agent execution
    ├── Tool
    ├── Guardrail
    ├── Handoff
    └── Workflow

observability
    │
    └── Event → SpanBuilder → TraceRecord

evaluation
    │
    ├── Dataset
    ├── EvalCase
    ├── TargetExecutor
    ├── Provider
    └── EvalResult

cost_analysis
    │
    └── usage / cost aggregation
```

主要问题：

### 3.1 Evaluation 丢失执行过程

Agent 实际执行：

```text
Input
 ↓
LLM
 ↓
Tool
 ↓
Tool Result
 ↓
LLM
 ↓
Handoff
 ↓
Sub Agent
 ↓
Answer
```

Evaluation 最终主要关注：

```text
Input → Output
```

因此无法天然评价：

```text
Tool selection
Tool arguments
Tool order
Agent loop
Handoff
Guardrail
Steps
Latency
Cost
Trajectory
```

---

### 3.2 Observability 在重新解释 Runtime

如果当前存在类似：

```text
Event name
   ↓
SpanBuilder 判断
   ↓
SpanKind
```

说明 Runtime Event 本身语义不够稳定。

目标应该变成：

```text
ToolCallStarted
ToolCallCompleted
LLMCallStarted
LLMCallCompleted
HandoffCompleted
```

Observability 不需要"猜"。

---

### 3.3 Evaluation 的核心抽象过度围绕 Provider

例如：

```text
RAGASProvider
DeepEvalProvider
```

容易导致：

```text
第三方评估框架
      ↓
定义 AgentLabKit Eval 能力
```

应该反过来：

```text
AgentLabKit Evaluator
      ↓
External Adapter
      ↓
RAGAS
```

---

### 3.4 Cost / Eval / Trace 存在事实重复

未来希望：

```text
Execution Facts
     │
     ├── Trace Projection
     ├── Cost Projection
     └── Eval Projection
```

而不是：

```text
Runtime
├── Observability collector
├── Cost collector
└── Eval collector
```

分别维护业务事实。

---

## 4. Execution Model v2 核心对象

第一阶段严格控制核心模型数量。

只定义：

```text
RuntimeEvent
AgentRun
TraceRecord
SpanRecord
```

Eval 层：

```text
DatasetExample
Evaluator
EvaluationResult
EvaluationRun
```

暂时不引入：

```text
Experiment
EvaluationJob
ReplaySession
RunArtifactGraph
```

等复杂实体。

---

## 5. AgentRun 设计

`AgentRun` 是本次重构最重要的对象。

建议：

```python
@dataclass
class AgentRun:
    run_id: str

    input: Any
    output: Any | None

    status: RunStatus

    target: RunTarget

    trace_id: str | None

    usage: RunUsage | None

    error: RunError | None

    started_at: datetime
    finished_at: datetime | None

    metadata: dict[str, Any]
```

其中：

```python
class RunStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

Target：

```python
@dataclass
class RunTarget:
    type: str

    agent_id: str | None
    agent_version: str | None

    workflow_id: str | None
    workflow_version: str | None
```

目标：

```text
Run 不绑定某一种 Agent 实现。

未来：

Agent
Workflow
Sub Agent
Evaluation Target

都可以形成 Run。
```

---

## 6. Run 与 Trace 的关系

必须明确：

```text
Run != Trace
```

定义：

```text
Run
=
一次业务执行

Trace
=
这次执行的详细观测记录
```

例如：

```text
Run #123

Input:
"退款订单123"

Output:
"退款已提交"

Status:
completed

Trace #abc
├── agent
├── llm
├── tool:get_order
├── tool:verify_identity
├── tool:refund
└── llm
```

因此：

```text
AgentRun.trace_id → TraceRecord
```

而不是：

```text
AgentRun 内嵌完整所有 Span
```

避免 Run 对 Trace Store 强耦合。

---

## 7. Runtime Event Model v2

这一阶段非常重要。

统一事件基类：

```python
@dataclass
class RuntimeEvent:
    event_id: str

    run_id: str
    trace_id: str

    span_id: str | None
    parent_span_id: str | None

    timestamp: datetime

    event_type: str

    attributes: dict[str, Any]
```

然后定义明确的语义事件。

---

### 7.1 Run Events

```text
RunStarted
RunCompleted
RunFailed
RunCancelled
```

---

### 7.2 Agent Events

```text
AgentStarted
AgentCompleted

AgentTurnStarted
AgentTurnCompleted
```

---

### 7.3 LLM Events

```text
LLMCallStarted
LLMCallCompleted
LLMCallFailed
```

Completed 至少携带：

```text
model
provider
tokens_input
tokens_output
latency
finish_reason
```

---

### 7.4 Tool Events

```text
ToolCallStarted
ToolCallCompleted
ToolCallFailed
```

至少包含：

```text
tool_name
arguments
result
duration
error
```

敏感信息允许后续通过 sanitizer 做脱敏。

---

### 7.5 Retrieval Events

```text
RetrievalStarted
RetrievalCompleted
RetrievalFailed
```

---

### 7.6 Guardrail Events

```text
GuardrailEvaluated
GuardrailBlocked
```

---

### 7.7 Multi-Agent Events

```text
HandoffStarted
HandoffCompleted

DelegationStarted
DelegationCompleted
```

---

### 7.8 Workflow Events

不要完全替换现有 WorkflowStreamEvent。

而是建立映射：

```text
WorkflowStreamEvent
        ↓
Semantic Runtime Event
```

或者后期让 Workflow Engine 直接发送标准 RuntimeEvent。

---

## 8. EventBus 的定位调整

EventBus 仍然保留。

但职责变成：

> Runtime Event Transport

而不是：

> Observability 专用基础设施。

结构：

```text
Runtime
   │
   ▼
EventBus
   │
   ├── TraceProjector
   ├── CostProjector
   ├── LiveStreamSubscriber
   └── Future Consumers
```

这样 EventBus 本身不会属于 observability。

---

## 9. Observability v2

Observability 不再负责理解业务事件。

它只负责：

```text
RuntimeEvent
    ↓
Trace Projection
```

建议：

```text
observability/
├── contracts.py
├── projector.py
├── store.py
├── query.py
└── exporters/
```

核心：

```python
class TraceProjector:

    def handle(
        self,
        event: RuntimeEvent,
    ) -> None:
        ...
```

例如：

```text
ToolCallStarted
      ↓
create TOOL span

ToolCallCompleted
      ↓
close TOOL span
```

不再出现：

```text
if event_name.startswith("tool_"):
```

这种隐式语义判断。

---

## 10. SpanKind 标准化

保留现有思想，但明确标准类型：

```text
RUN
AGENT
AGENT_TURN
LLM_CALL
TOOL_CALL
RETRIEVAL
GUARDRAIL
HANDOFF
DELEGATION
WORKFLOW
WORKFLOW_STEP
CUSTOM
```

不要让第三方 Provider 类型进入核心 SpanKind。

---

## 11. Cost Analysis v2

Cost Analysis 不应该再次监听业务层的各种模型调用逻辑。

优先消费：

```text
LLMCallCompleted
```

其中已经存在：

```text
model
provider
input_tokens
output_tokens
```

CostProjector：

```python
class CostProjector:

    def handle(
        self,
        event: LLMCallCompleted,
    ):
        ...
```

生成：

```text
CostRecord
```

关联：

```text
run_id
trace_id
agent_id
model
```

未来 Cost Analysis 就可以天然支持：

```text
cost per run
cost per agent
cost per workflow
cost per experiment
```

---

## 12. Evaluation v2 总体设计

Evaluation 改为：

```text
DatasetExample
      +
AgentRun
      +
Trace
      ↓
Evaluator
      ↓
EvaluationResult
```

不再：

```text
input
 ↓
executor
 ↓
str output
 ↓
provider
```

---

## 13. Evaluator 核心接口

建议：

```python
class Evaluator(Protocol):

    @property
    def name(self) -> str:
        ...

    async def evaluate(
        self,
        example: DatasetExample,
        run: AgentRun,
        context: EvaluationContext,
    ) -> EvaluationResult:
        ...
```

EvaluationContext：

```python
@dataclass
class EvaluationContext:
    trace: TraceRecord | None

    spans: list[SpanRecord]

    metadata: dict[str, Any]
```

---

## 14. EvaluationResult

统一结果：

```python
@dataclass
class EvaluationResult:
    evaluator: str

    status: EvaluationStatus

    score: float | None

    label: str | None

    message: str | None

    details: dict[str, Any]
```

例如：

```text
ToolCalledEvaluator

status = FAIL

message =
"Expected tool 'verify_identity' was not called."
```

Evaluation 不应该强制所有 evaluator 输出数字。

允许：

```text
PASS / FAIL
score
label
structured details
```

---

## 15. Provider 重构

现有：

```text
Provider
├── RAGAS
└── Future DeepEval
```

迁移为：

```text
Evaluator
│
├── Native Evaluators
│
└── External Adapters
      ├── RagasEvaluator
      └── ...
```

ProviderRegistry 可以暂时保留兼容层。

但核心 API 不再暴露：

```text
provider.evaluate(...)
```

而是：

```text
runner.run(
    evaluators=[...]
)
```

---

## 16. 第一批 Native Evaluator

不要一开始做复杂 LLM Judge。

第一批优先实现 deterministic evaluator。

---

### ToolCalledEvaluator

```python
ToolCalled("get_order")
```

---

### ToolNotCalledEvaluator

```python
ToolNotCalled("delete_user")
```

---

### ToolCallCountEvaluator

```python
ToolCallCount(
    tool="search",
    max_calls=3,
)
```

---

### ToolArgumentsEvaluator

```python
ToolArguments(
    tool="refund",
    match={
        "order_id": "123"
    },
)
```

---

### MaxStepsEvaluator

```python
MaxSteps(8)
```

---

### LatencyEvaluator

```python
Latency(max_ms=3000)
```

---

### CostEvaluator

```python
Cost(max_usd=0.05)
```

---

### ErrorEvaluator

```python
NoUnhandledError()
```

---

## 17. Trajectory Model

不要直接让 evaluator 操作 Span。

增加轻量：

```python
Trajectory
```

定义：

```python
@dataclass
class TrajectoryStep:
    kind: str
    name: str
    attributes: dict
```

例如：

```text
Trajectory
├── agent:customer_service
├── tool:get_customer
├── tool:get_order
├── handoff:refund_agent
├── tool:verify_policy
├── tool:refund
└── agent:final_answer
```

由：

```text
Trace
 ↓
TrajectoryBuilder
```

得到。

---

## 18. Trajectory Evaluator

第一版支持：

```text
STRICT
SUBSET
SUPERSET
UNORDERED
```

示例：

```python
TrajectoryEvaluator(
    expected=[
        Tool("get_order"),
        Tool("verify_identity"),
        Tool("refund"),
    ],
    mode="subset",
)
```

后续再添加：

```text
Before(A, B)

After(A, B)

Never(A)

MaxOccurrences(A)

ContainsSequence(...)
```

---

## 19. Dataset v2

现有 EvalCase 改造为：

```python
@dataclass
class DatasetExample:
    id: str

    input: Any

    expected_output: Any | None

    expectations: list[Expectation]

    metadata: dict[str, Any]

    source_run_id: str | None
```

关键：

```text
expected_output
```

必须变成 optional。

因为 Agent Eval 经常并不存在唯一正确回答。

---

## 20. Expectation

Expectation 是 Dataset 描述"正确行为"的数据。

例如：

```text
ToolCalled
ToolNotCalled
ExpectedTrajectory
OutputContains
OutputSchema
```

注意：

```text
Expectation != Evaluator
```

Expectation：

> 数据描述

Evaluator：

> 执行评价逻辑

例如：

```python
Expectation:
ToolCalled("verify_identity")

Evaluator:
ToolExpectationEvaluator
```

这样 Dataset 不依赖具体 evaluator 实现。

---

## 21. Run → Dataset

必须实现：

```python
dataset.add_run(
    run,
    ...
)
```

流程：

```text
发现一个真实失败 Run
        ↓
Add to Dataset
        ↓
补充 expectations
        ↓
成为 regression case
```

这是整个 Eval 系统最重要的闭环之一。

---

## 22. EvaluationRun

暂时不引入 Experiment。

保留更轻量的：

```python
@dataclass
class EvaluationRun:
    id: str

    dataset_id: str

    target: RunTarget

    results: list[ExampleEvaluation]

    summary: EvaluationSummary
```

逻辑：

```text
Dataset
   ↓
Target
   ↓
run each example
   ↓
AgentRun*
   ↓
Evaluators
   ↓
EvaluationRun
```

---

## 23. Compare

实现：

```python
compare(
    baseline: EvaluationRun,
    candidate: EvaluationRun,
)
```

输出：

```text
Improved
Regressed
Unchanged
```

同时比较：

```text
pass rate
score
cost
latency
steps
tool calls
```

这样已经具备 Experiment 的核心能力。

不要现在增加 Experiment 表。

---

## 24. Replay MVP

Replay 第一版定义非常简单：

```python
async def replay(
    run: AgentRun,
    target: RunTarget | None = None,
) -> AgentRun:
```

语义：

```text
Old Run
   │
   ├── reuse input
   ├── reuse context where safe
   │
   ▼
New Target
   │
   ▼
New Run
```

暂时不实现：

```text
freeze tools
freeze retrieval
fork span
resume mid execution
```

---

## 25. CLI

增加：

```bash
agentlab eval
```

例如：

```bash
agentlab eval eval.yaml
```

配置：

```yaml
dataset: refund-regression

target:
  agent: customer-service
  version: latest

evaluators:

  - type: tool_called
    tool: verify_identity

  - type: max_steps
    value: 8

  - type: trajectory
    mode: subset

  - type: latency
    max_ms: 3000
```

结果：

```text
200 examples

Passed:     188
Failed:      12

Pass rate: 94.0%

Latency:
P50 1.4s
P95 2.7s

Cost:
Avg $0.013

Failed Cases:
#12 missing verify_identity
#38 trajectory mismatch
...
```

失败时：

```text
exit code = 1
```

供 CI 使用。

---

## 26. 包结构建议

最终建议逐步迁移到：

```text
packages/

agent_runtime/
├── runtime/
├── events/
├── tools/
├── guardrails/
├── orchestration/
└── workflow/


observability/
├── contracts/
├── projector/
├── store/
├── query/
└── exporters/


evaluation/
├── datasets/
├── runner/
├── evaluators/
│   ├── rule/
│   ├── trajectory/
│   ├── llm_judge/
│   └── adapters/
│       └── ragas/
├── results/
├── compare/
└── cli/


cost_analysis/
├── projector/
├── pricing/
├── store/
└── query/
```

暂时不创建：

```text
packages/run
```

Run contract 可以先放：

```text
agent_runtime/contracts/run.py
```

如果未来 Run 被：

```text
Agent Runtime
Evaluation
Replay
Workflow
External Runtime
```

广泛依赖，再独立成 package。

---

## 27. 依赖方向

目标依赖：

```text
                  agent_runtime
                       │
                       │ produces
                       ▼
                 RuntimeEvent
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
 observability    cost_analysis   backend
          │
          │
          ▼
       Trace
          │
          ▼
     evaluation
```

但是需要避免：

```text
agent_runtime
    ↓
evaluation
```

Runtime 永远不知道 Evaluation 的存在。

Evaluation 可以依赖 runtime contracts。

---

## 28. 迁移阶段

### Phase 0：冻结现状 ✅

> **状态：已完成** (2026-08-29)

目标：

建立重构前安全网。

任务：

```text
补 Runtime 核心测试

补 EventBus 测试

补 Trace 构建测试

补 Evaluation Runner 测试

补 Cost Aggregation 测试
```

建立关键 golden tests。

完成标准：

```text
现有主要行为全部有回归测试。
```

完成情况：

- `packages/agent_runtime/tests/test_event_bus.py` — 15 tests: subscribe/unsubscribe、emit 顺序、error isolation、sync+async listener、clear、事件类型覆盖
- `packages/observability/tests/test_trace_building.py` — 14 tests: root span 检测、token 聚合、_convert_span、priority 驱动 span 保留、buffer overflow、envelope 状态
- `packages/evaluation/tests/test_runner_edge_cases.py` — 10 tests: target_executor 调用、error handling、metric 聚合、metric name 解析
- `packages/cost_analysis/tests/test_contracts.py` — 14 tests: dataclass 构造、枚举值、frozen 特性、边界条件

---

### Phase 1：Runtime Event v2 ✅

> **状态：已完成** (2026-08-29)

新增：

```text
RuntimeEvent
RunStarted
RunCompleted
LLMCall*
ToolCall*
Guardrail*
Handoff*
```

暂时：

```text
旧事件继续发送
+
新事件同时发送
```

Dual Emit。

不要一次删旧 API。

完成标准：

```text
一次 Agent Run 能产生完整 semantic event stream。
```

完成情况：

- `packages/agent_runtime/src/agent_runtime/events_v2.py` — 23 个语义事件类型：RunStarted/Completed/Failed/Cancelled, AgentStarted/Completed/AgentTurnStarted/Completed, LLMCallStarted/Completed/Failed, ToolCallStarted/Completed/Failed, RetrievalStarted/Completed/Failed, GuardrailEvaluated/Blocked, HandoffStarted/Completed, DelegationStarted/Completed
- `packages/agent_runtime/tests/test_events_v2.py` — 70 tests: 构造、默认值、event_type 唯一性、枚举、序列化
- `packages/agent_runtime/tests/test_dual_emit.py` — 6 tests: v2 run/llm/tool 事件发射、run_id/trace_id 传递、旧事件兼容
- `packages/agent_runtime/src/agent_runtime/runtime/loop.py` — Dual Emit 集成：run_agent_loop 同时发射旧事件和 v2 语义事件

---

### Phase 2：AgentRun

修改 Runtime：

```python
result = await runtime.run(...)
```

逐步返回：

```text
AgentRun
```

而不是零散：

```text
message / usage / error
```

为旧调用增加 compatibility adapter。

完成标准：

```text
所有核心执行路径最终都能形成 AgentRun。
```

包括：

```text
normal agent
workflow
handoff
delegation
```

---

### Phase 3：Observability Projection

增加：

```text
RuntimeEvent
 ↓
TraceProjector
```

旧 SpanBuilder 保留。

双轨比较：

```text
Old Trace
VS
New Trace
```

在测试中验证关键 Span 一致。

确认稳定后：

```text
删除旧 event-name inference。
```

完成标准：

```text
Observability 不再依赖事件命名猜测。
```

---

### Phase 4：Cost Projection

将成本统计迁移到：

```text
LLMCallCompleted
```

验证：

```text
旧 cost
=
新 cost
```

允许极小 rounding 差异。

完成标准：

```text
Cost 数据完全可以从 execution events 生成。
```

---

### Phase 5：Evaluation Core v2

新增：

```text
DatasetExample
Evaluator
EvaluationResult
EvaluationContext
EvaluationRun
```

旧：

```text
EvalCase
Provider
```

暂时兼容。

实现 adapter：

```text
Old EvalCase
    ↓
DatasetExample

RAGASProvider
    ↓
RagasEvaluator
```

完成标准：

```text
RAGAS 能通过新 Evaluator API 工作。
```

---

### Phase 6：Agent Native Evaluators

按顺序：

```text
ToolCalled
ToolNotCalled
ToolArgs
MaxSteps
Latency
Cost
NoError
Trajectory
```

完成标准：

可以对一个完整 AgentRun 做：

```text
behavior evaluation
```

而不需要 LLM judge。

---

### Phase 7：Dataset Regression

增加：

```text
Run → DatasetExample
```

以及：

```text
Dataset
 ↓
EvaluationRun
```

完成标准：

可以将一次失败 Run 变成永久 regression case。

---

### Phase 8：Compare

实现：

```text
EvaluationRun A
        VS
EvaluationRun B
```

完成标准：

输出：

```text
improved
regressed
unchanged
```

并支持 case-level diff。

---

### Phase 9：Replay MVP

实现：

```text
Historical Run
      ↓
reuse input
      ↓
new target
      ↓
New Run
```

完成标准：

用户可以：

```text
Run #123
 ↓
Replay with Agent v2
 ↓
Compare
```

---

### Phase 10：CLI + CI

新增：

```bash
agentlab eval
```

以及：

```text
eval.yaml
```

支持：

```text
threshold
exit code
baseline comparison
```

最终：

```text
git push
   ↓
CI
   ↓
agentlab eval
   ↓
regression detected
   ↓
FAIL
```

---

## 29. 删除阶段

只有新架构稳定之后才能删除：

```text
Legacy event inference
Legacy SpanBuilder paths
Legacy TargetExecutor string-only API
Provider-centric public API
duplicate cost collection
```

删除标准：

```text
核心调用方全部迁移

测试全部通过

不存在隐式兼容依赖
```

---

## 30. 数据库迁移原则

第一阶段尽量：

```text
Additive Migration
```

例如增加：

```text
run_id
trace_id
source_run_id
```

而不要立刻删除旧字段。

流程：

```text
add column
 ↓
dual write
 ↓
backfill
 ↓
switch read
 ↓
stop old write
 ↓
drop old column
```

---

## 31. API 兼容策略

因为当前还是个人开源项目，可以接受 breaking change。

但是仍然建议：

```text
v1 API
 ↓
Deprecation warning
 ↓
v2 Adapter
```

至少保留一个版本周期。

如果重构成本过高，可以直接：

```text
AgentLabKit 0.x
```

明确允许 breaking API。

---

## 32. 测试重点

本次重构测试优先级：

### Runtime Event tests

确保：

```text
ToolStarted
ToolCompleted
```

严格成对。

---

### Run tests

确保：

```text
success
failure
cancel
handoff
workflow
```

都形成合法 Run。

---

### Trace Projection tests

输入：

```text
RuntimeEvent[]
```

输出：

```text
Trace
```

必须 deterministic。

---

### Evaluator tests

全部 native evaluator 做纯单元测试。

---

### Regression tests

固定：

```text
fake AgentRun
fake Trace
```

避免调用真实 LLM。

---

## 33. 一个关键设计要求：Evaluation 测试不能依赖真实模型

例如：

```text
FakeRunFactory
```

应该成为测试工具。

```python
run = FakeRunFactory.create(
    tools=[
        tool_call("get_order"),
        tool_call("refund"),
    ],
    output="done",
)
```

然后：

```python
result = await evaluator.evaluate(...)
```

这样 Agent Eval 本身是 deterministic 的。

---

## 34. 第一阶段最终 Demo

完成 Phase 1～8 后，应该能够展示：

```python
run = await agent.run(
    "退款订单123"
)

dataset.add_run(
    run,
    expectations=[
        ToolCalled("verify_identity"),
        ToolCalled("get_order"),
        ToolCalled("refund"),
    ],
)
```

然后：

```bash
agentlab eval refund-regression.yaml
```

输出：

```text
Agent: refund-agent@v18
Dataset: refund-regression

Cases: 100

✓ Passed: 96
✗ Failed: 4

Tool expectations: 98%
Trajectory:        96%
Latency:           PASS
Cost:              PASS
```

再：

```text
v17 vs v18

Improved   11
Regressed   2
Same       87
```

点击 / 查看 regression：

```text
Case #42

Expected:
get_order
→ verify_identity
→ refund

Actual:
get_order
→ refund

FAILED:
Missing required step verify_identity
```

这应该成为 Execution Model v2 的第一个完整产品故事。

---

## 35. 成功标准

这次重构完成后，应该能够回答下面的问题：

```text
一次 Agent 执行是什么？
→ AgentRun

执行过程中发生了什么？
→ RuntimeEvent

如何观察执行过程？
→ Trace

一次 LLM 花了多少钱？
→ Cost projection

Agent 有没有以正确方式完成任务？
→ Evaluator

真实失败如何成为测试用例？
→ Run → DatasetExample

新版本有没有退化？
→ EvaluationRun Compare

历史问题能不能重新执行？
→ Replay
```

如果这些问题分别只有一个清晰答案，说明架构重构成功。

---

## 36. 最终架构

```text
                         AgentLabKit

                         ┌──────────┐
                         │ Runtime  │
                         └────┬─────┘
                              │
                              ▼
                        Runtime Events
                              │
                              ▼
                           AgentRun
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
          Observability      Cost         Streaming
               │
               ▼
             Trace
               │
               │
               ▼
          Evaluation
               │
       ┌───────┼──────────┐
       ▼       ▼          ▼
    Rules   Trajectory   Judge
       │       │          │
       └───────┼──────────┘
               ▼
        EvaluationRun
               │
          ┌────┴────┐
          ▼         ▼
       Compare    Dataset
          │         ▲
          │         │
          │       Run
          │
          ▼
      Regression

Historical Run
      │
      ▼
    Replay
      │
      ▼
   New Run
```

核心设计原则保持一句话：

> Runtime 负责产生事实，Event 负责描述事实，Run 负责界定一次执行，Trace 负责观察事实，Evaluation / Cost / Replay 只消费事实。

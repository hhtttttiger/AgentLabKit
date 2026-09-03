# AgentLabKit Application

`application` hosts reusable, framework-neutral platform use cases: execution,
replay, dataset capture, and evaluation.

It is not a replacement for module services. CRUD and simple projection queries
may continue to be called directly by FastAPI. Application contracts are not
HTTP contracts, and this package has no dependency on `backend`, FastAPI, or
Starlette.

Application coordinates domain capabilities; it does not create execution or
trace identity, construct `AgentRun`, manufacture runtime events, or turn a
`run_id` into a dataset `example_id`. Runtime, Dataset, Trace, and Evaluation
remain the owners of those facts.

Use cases are ordinary Python objects and are invoked with `await
use_case.execute(command)` (streaming is exposed by `ExecuteAgent.stream`).
Adapters belong at composition roots such as the backend.

## Current evaluation boundary

`EvaluateDataset` owns platform orchestration for the agent target: it loads the
configuration and dataset, starts the persisted run, iterates examples, asks
Runtime to execute each target, obtains optional trace evidence, invokes the
Evaluation public case capability, records results, and completes or fails the
run. The Evaluation package owns judging semantics, metric execution, verdicts,
and evaluator-failure behavior; the backend adapter must not calculate
PASS/FAIL or call private Evaluation methods.

The HTTP module service creates the pending persistence record and schedules the
use case through `BackgroundTasks`. That creation step is a compatibility
boundary, not a second execution orchestrator: after scheduling, the use case
owns the `pending -> running -> completed/failed` lifecycle transitions through
`EvaluationRunStore`. Backend adapters only translate ORM/configuration/runtime
capabilities and persist projections. Runtime remains the owner of execution
facts and identity.

Only `target_type == "agent"` uses this application path today. The
`rag_pipeline` target remains on the legacy runner intentionally. `ReplayRun` is
production-wired by the backend: it reads a durable Run with `RunReader`,
resolves the exact stored agent version, and executes through `RunExecutor` and
Runtime. Dataset capture and additional evaluation use cases remain deferred.

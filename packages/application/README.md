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

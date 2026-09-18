# AgentLabKit

> Enterprise Agent Engineering Platform

从构建 Agent、运行真实任务，到观察、回放、评估和比较，让每一次执行都成为下一次改进的依据。

[概览](#概览) · [亮点](#亮点) · [你可以用它做什么](#你可以用它做什么) · [核心概念](#核心概念) · [快速开始](#快速开始) · [文档](#文档)

## 概览

AgentLabKit 是面向企业内部 Agent 开发、运行、评估与持续改进的
Agent Engineering Platform，同时也可以作为 Python library 使用。

它的核心闭环是：

```text
Build → Run → Observe → Capture Evidence → Evaluate → Improve → Repeat
```

它关注的不是“做一个会聊天的机器人”，也不是与 Codex、Claude Code 等通用
Coding Agent 竞争，而是帮助企业把自己的 Agent 当成一个可以持续开发、验证
和交付的软件系统：

```text
构建 Agent → 运行真实任务 → 检查执行 → 保存案例 → 评估改进 → 比较版本
```

你可以使用它构建 Agent、连接模型与工具、加入 Knowledge/RAG、运行真实请求，随后回答这些工程问题：

- Agent 实际执行了什么？
- 它使用了哪些工具和知识？
- 哪些失败案例值得保留下来？
- 新版本是真的变好了，还是只是换了一批样本？
- 如何把一个可行的实验变成可复用、可交付的 Agent 能力？

AgentLabKit 适合作为团队内部的 Agent 开发基础，也适合作为业务系统背后的 Agent 能力库。

## 亮点

| 能力 | 说明 |
| --- | --- |
| 🧩 Agent 构建 | 组合企业自己的 Instructions、Model、Tools、Knowledge、Memory、Guardrails 和 Workflow，形成可发布的 Agent 版本 |
| ▶️ 真实执行 | 记录每一次真实 Run，而不是只展示演示数据或模型输出 |
| 🔍 执行检查 | 查看 Run 与 Trace，了解响应、工具调用、检索和错误发生在哪里 |
| 🔁 回放与复现 | 对历史 Run 重新执行，验证 Agent 版本、提示词或能力调整后的结果 |
| 📚 Knowledge / RAG | 准备知识、测试 Retrieval，并区分没有检索、检索无结果和检索失败 |
| 🧪 Dataset / Evaluation | 将真实 Run 保存为测试资产，批量评估 Agent，并比较 Baseline 与 Candidate |
| 🖥️ 多种使用方式 | 提供可复用的 Python packages、共享 Server 平台和 local-first Desktop workbench |
| 🔌 可集成 | 可通过 HTTP/SSE 接入业务后端，也可以直接在自己的应用中组合 package 层能力 |

## 你可以用它做什么

### 构建一个可工作的 Agent

配置模型、Tools 和 Knowledge，发布一个可执行的 Agent 版本，然后用真实请求测试它，而不是停留在 prompt 草稿阶段。

### 建立 Agent 的改进闭环

```text
Create Agent
    ↓
Configure → Publish → Test
    ↓
Inspect Run → Diagnose → Add to Dataset
    ↓
Evaluate Dataset → Modify Agent → Compare
```

真实执行中的失败、边界情况和高价值样本，都可以沉淀为下一轮评估和迭代的资产。

### 诊断 Knowledge 和 Retrieval

Agent 的回答不理想时，先判断问题发生在哪一层：

```text
没有发生 Retrieval ≠ Retrieval 没有结果 ≠ Retrieval 失败
```

AgentLabKit 将检索行为和 Agent 响应分开观察，帮助你判断应该调整知识库、检索配置，还是 Agent 本身的指令与行为。

### 为业务应用提供 Agent 能力

业务应用可以保留自己的用户、订单、权限和业务状态，通过 AgentLabKit 使用 Agent、Knowledge、Tools、Runs 和 Evaluation。业务产品不需要依赖 Agent 内部循环，也不需要把业务对象伪装成 Agent 的执行身份。

### 在本地工作，或接入共享平台

| 使用方式 | 适合场景 |
| --- | --- |
| Python packages | 在自己的 CLI、worker、服务或产品中快速组合 Agent 能力 |
| Web 平台 | 团队共享 Agent、Knowledge、Run、Dataset 和 Evaluation 的 Enterprise Agent Engineering 平台 |
| Tauri Desktop | 面向 Agent Developer 的 local-first Agent Engineering workbench |
| HTTP/SSE API | 由业务后端调用 Agent，并将执行结果接回自己的产品流程 |

Desktop 是面向 Agent Developer 的 local-first workbench；Server/Web 平台则是面向团队和企业环境的 shared Agent Engineering Platform。两者可以使用同一套核心 Agent 能力，但不要求拥有相同的产品界面。

## 核心概念

| 概念 | 含义 |
| --- | --- |
| **Agent** | 一组可配置、可发布、可执行的模型与能力组合 |
| **Run** | 一次真实的 Agent 执行 |
| **Trace** | 对一次 Run 的观测和诊断信息 |
| **Dataset** | 可复用的测试样本集合 |
| **Evaluation Run** | 使用一组 Dataset 样本评估 Agent 的一次过程 |
| **Knowledge** | Agent 可以使用的资料集合 |
| **Retrieval** | 一次实际发生的知识检索行为 |

其中，Run 是执行事实，Trace 是观测；Dataset 中的样本身份也不同于 Run 身份。理解这几个概念，就能读懂 AgentLabKit 的主要工作流。

## 快速开始

### 使用 Docker 体验 Web 平台

要求：Docker 和 Docker Compose v2。

```bash
git clone https://github.com/hhtttttiger/AgentLabKit.git
cd AgentLabKit
cp .env.example .env
docker compose up --build
```

启动后访问：

- Web 控制台：<http://localhost:3000/admin/>
- API 健康检查：<http://localhost:8000/health>
- 默认账号：`admin` / `admin`

### 作为开发库使用

如果你想在自己的应用、CLI 或 worker 中直接组合 Agent 能力，请从 [Library-first Agent 开发指南](docs/guides/building-agents-with-packages.md) 开始。这条路径不要求启动完整的 Web 平台。

### 使用 Desktop

当前 Desktop 使用 Tauri shell 和 React frontend，支持 Local Mode 与 Server Mode：

```bash
cd frontend/admin
npm install
npm run desktop:dev
```

Desktop 的产品定位与运行模式见 [Desktop Product Projection](docs/architecture/desktop-product-projection.md) 和 [Desktop modes](docs/desktop-modes.md)。

## 当前定位

AgentLabKit 的核心价值是“让企业 Agent 工程变得可验证、可复用、可持续改进”。
Native Agent 是 AgentLabKit 的 Reference / Enterprise Agent Runtime；外部 Agent
可以在有稳定集成时参与 Capture / Import、Replay 或 Evaluation，但外部 Agent 的
interactive session UX 不是 AgentLabKit 的默认 ownership。

AgentLab owns the Agent Engineering lifecycle and long-lived engineering assets：
Run、Case、Dataset、Evaluation、Compare、Replay，以及 Observability / Cost facts。
Agent implementation 是 execution component，不是产品模型中长期不变的中心。

当前项目同时维护三条入口：

1. **Package-first**：快速开发和组合 Agent 的通用库。
2. **Web platform**：面向团队和企业环境的 shared Agent Engineering Platform。
3. **Desktop workbench**：面向 Agent Developer 的本地 Agent Engineering 工作台。

这三条入口共享核心执行能力，但各自面向不同的使用场景。

## 文档

- [产品说明](PRODUCT.md) — 产品目标、用户旅程和产品语言。
- [文档导航](docs/README.md) — 当前权威文档、历史记录和 Deprecated 文档的状态约定。
- [Library-first Agent 开发](docs/guides/building-agents-with-packages.md) — 不依赖 Web 平台，直接使用 packages 构建 Agent。
- [业务应用集成](docs/guides/building-business-applications.md) — 从业务后端接入 AgentLabKit。
- [Desktop Product Projection](docs/architecture/desktop-product-projection.md) — Desktop 如何投影平台能力。
- [Desktop modes](docs/desktop-modes.md) — Local Mode 和 Server Mode 的运行方式。
- [架构文档](docs/architecture/) — Runtime、Run、Trace、HTTP adapter 和 streaming contract 的详细规则。
- [Application package](packages/application/README.md) — framework-neutral platform use cases。

## 参与开发

如果你要修改仓库本身，请先阅读 [AGENTS.md](AGENTS.md) 和对应目录下的开发说明。后端、package、frontend 和 Desktop 的验证命令也集中在各自的文档中。

## 许可证

MIT

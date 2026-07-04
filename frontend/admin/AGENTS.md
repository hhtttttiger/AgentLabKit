# admin — React 管理后台

> **定位**：AgentLabKit 的 React 19 + TypeScript 管理后台（Vite 构建）。模型管理、Agent 管理、知识库、AI 对话与监控的统一前端实现，运行时通过 HTTP / SSE 调用 backend。

## 系统中的角色

```
源码 (React 19 · TypeScript · Vite)
    │   npm run build   (vite build --base=/admin/)
    ▼
dist/ 静态产物
    │   Dockerfile 多阶段: node:22-alpine 编译 → nginx:alpine 服务
    ▼
nginx (nginx.conf)  ──/admin/ (SPA fallback)──▶  浏览器
                          │
                          ▼  运行时 fetch / SSE
                     backend (FastAPI HTTP API)
```

本模块是 AgentLabKit 的唯一前端入口：通过 backend 的 HTTP API 取数据、SSE 取流式输出。

## 关键文件

| 文件 / 目录 | 说明 |
|------|-------------|
| `package.json` | 前端依赖与 `dev/check/test/build` 脚本 |
| `src/app/*` | 应用入口、路由、模块注册与全局 shell |
| `src/shared/*` | API、错误处理、通用 UI、测试辅助 |
| `src/shared/agent-trace/*` | Agent 执行轨迹共享视图组件与契约（`AgentTraceView`、`AgentExecutionTrace`） |
| `src/modules/model-management/*` | 模型管理模块与四类资源实现 |
| `src/modules/knowledge-base/*` | 知识库模块：知识库 CRUD、文档/QA 管理、检索测试、召回榜单与详情抽屉 |
| `src/modules/ai-chat/*` | AI 对话模块：支持模型卡与 Agent 两种模式，含流式 SSE 解析、轨迹合并与历史管理 |
| `src/modules/agent-management/*` | Agent 管理模块：定义/版本/工具/技能/MCP/审计，审计详情复用共享轨迹视图 |
| `Dockerfile` | 多阶段构建：node:22-alpine 编译 + nginx:alpine 静态服务 |
| `nginx.conf` | nginx 配置：`/admin/` SPA fallback、gzip、资产缓存、健康检查 |
| `.dockerignore` | Docker 构建时排除 node_modules/dist 等 |

## 开发约定

- 当前目录是正式后台实现，不要按占位/模板目录对待。
- 目录分层固定为 `app / shared / modules`，不要重新堆回无边界的 `pages/components/stores` 平铺结构。
- 资源型实现优先放在 `src/modules/<module>/resources/<resource>` 下，保持 API、hooks、types、页面和表单在资源目录内部自洽。
- 列表页统一复用 `shared/ui/ManagementListFrame`，工具栏、滚动区、分页区分层明确；底部分页/状态区不应跟随表格主体一起滚动。
- **路由 basename**：`src/app/router.tsx` 使用 `import.meta.env.BASE_URL` 动态设定 basename，构建时通过 `vite build --base=/admin/` 注入。本地开发无需手动设置。
- **容器化部署**：Dockerfile 使用多阶段构建（node build → nginx serve），nginx 在 `/admin/` 路径下提供 SPA 服务。AKS Ingress 将 `/admin` 路由到此服务。

## 测试要求

- 修改前端后至少运行：
  - `npm run check`
  - `npm run test`
  - `npm run build`

## 常见模式

- 远程数据统一通过 `shared/api/client.ts` + TanStack Query 处理。
- 表单优先结构化输入；复杂字段通过共享 `JsonEditor` 承载。
- 模块扩展从 `src/app/modules.tsx` 注册入口接入，不要直接把新模块写死在多个壳层文件里。
- **Agent 轨迹可视化**：`shared/agent-trace/` 提供 `AgentTraceView` 组件和 `AgentExecutionTrace` 契约，被 `ai-chat` 和 `agent-management` 两个模块复用。`ai-chat/lib/agent-trace-merge.ts` 封装了从 SSE event 到 `AgentExecutionTrace` 的纯函数合并逻辑（`mergeAgentTrace` / `buildStepFromEvent`），带完整单元测试。
- **SSE 解析**：`ai-chat/api.ts` 提供统一 `streamSse()` 基础函数，`streamCardChatMessage` 和 `streamAgentChatMessage` 分别消费。`AgentStreamEvent.type` 是联合类型 `AgentStreamEventType`，确保 switch 穷尽检查。
- **Agent 审计详情**：`agent-management/resources/audits/` 下的 `AuditDetailDrawer` 复用 `AgentTraceView` 展示运行轨迹。
- 模型目录中的关联字段优先复用已有资源列表做选择，不要把模型卡、连接配置等已存在资源退回为手工自由输入。
- 实例创建时可通过 `/api/llm-catalog/connection-profiles/{connectionProfileKey}/provider-models` 获取 Provider 模型与部署名建议；前端允许在建议之外切回"自定义输入"。
- **知识库管理**：`knowledge-base/pages/tabs/KbOverviewTab.tsx` 右侧展示可折叠的 `召回文档 / QA Top 100` 榜单；`KbDocumentsTab.tsx` 的详情抽屉通过 `useDocumentDetail()` 获取实时文档详情，并显示 `累计被召回次数` 与 `最近召回时间`。

## 视觉偏好系统

admin 右上角 UserMenu 包含四类视觉偏好，统一以 `localStorage` 持久化、模块导入时同步应用（防 flash）：

| 偏好 | Hook | localStorage key | 作用点 |
|------|------|-----------------|--------|
| 深色/浅色/跟随系统 | `useTheme()` (Context) | `ai-admin-theme` | `html[data-theme]` |
| 主题色 | `useTheme()` (Context) | `ai-admin-accent` | `html[data-accent]` |
| 动画开关 | `useMotion()` | `ai-admin-motion` | `html.classList` → `motion-enabled` |
| 缩放比例 | `useZoom()` | `ai-admin-zoom` | `html.style.zoom` |
| 语言 | `useAdminLocale()` / `i18next` | `ai-admin-locale` | `UserMenu` 偏好区、`html[lang]`、登录页/菜单文案 |

- 首轮语言切换只放在已登录后的 `UserMenu` 中；登录页不新增独立切换器，而是读取已保存语言或浏览器默认语言。
- 当前已覆盖导航、模块壳层和首批首页级页面（如知识库列表、模型监控概览、系统监控）的前端静态文案；新增页面时优先把 `title / description / empty / loading / action` 文案接入 `src/shared/i18n/resources.ts`。

### 主题色扩展

主题色通过 `html[data-accent]` 切换，CSS token 覆盖定义在 `src/shared/theme/tokens/semantic-accent.css`。新增主题色需要：
1. 在 `types.ts` 的 `AccentColor` 联合类型里加新值
2. 在 `semantic-accent.css` 里加对应 `[data-accent="<name>"]` 的 token 覆盖块
3. 在 `AccentPicker.tsx` 的 `ACCENT_OPTIONS` 数组里加一项（含 swatch 色值）

默认色 `blue` 不写入 `data-accent`（attribute 移除），其他色才写入。

### 缩放比例注意事项

缩放档位（`auto / 100% / 90% / 80%`）通过 `src/shared/zoom/useZoom.ts` 管理：

- **`auto` 档**（默认）：移除 `html.style.zoom`，由 `src/styles/index.css` 里的 CSS 媒体查询自动接管（`@media (max-width: 1400px) and (min-width: 961px) { html { zoom: 0.875 } }`）。**不要在两处重复维护缩放逻辑**，CSS 媒体查询只负责 `auto` 的兜底行为。
- **手动档**：`html.style.zoom` 内联 style 优先级高于媒体查询，会完全接管缩放。

**后续开发需注意 `zoom` 的三个已知行为：**

1. **媒体查询不感知 zoom**：`@media (max-width: N)` 和 JS `matchMedia` 始终基于未缩放的 CSS 视口像素。`zoom: 0.8` 会让视觉内容变小但断点仍在原始像素触发。写响应式判断逻辑时按原始像素值设计即可，无需补偿。
2. **Canvas 元素不受 CSS zoom 影响**：引入 ECharts、Chart.js 等 canvas 图表时，需手动读取当前 zoom 值并传给图表的 resize 计算：
   ```ts
   const zoom = parseFloat(document.documentElement.style.zoom || '1');
   // 传给图表 resize / canvas scale
   ```
3. **`getBoundingClientRect()` 返回缩放后坐标**（Chrome/Edge 现代版本），拖拽、tooltip 定位等坐标计算在 zoom 环境下通常无需额外处理。

## 另见

- [根 AGENTS.md](../../AGENTS.md) — 全局架构与文档索引
- [backend/AGENTS.md](../../backend/AGENTS.md) — 本前端调用的 HTTP API 与 SSE 端点

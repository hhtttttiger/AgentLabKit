# Desktop Python components

> Product status: the old PySide6 Desktop shell is deprecated. The current
> Desktop product is `frontend/admin` + `frontend/admin/src-tauri`.
>
> This directory still contains the active Python Local Mode API and tools used
> by Tauri. Do not remove or rename `local/` or `tools/` as part of the legacy
> client deprecation.

## 职责

`desktop/local` 是 Tauri Local Mode 启动的 Python API；旧的 PySide6 shell
（`main.py`、`app/`、`ui/`、`capture/`、`storage/`、`utils/`）仅保留作历史参考，已废弃。

Desktop 产品按 Work Objects 和 Work Actions 组织，不按底层 Module 组织；
详细的 Product Projection 原则见
[`docs/architecture/desktop-product-projection.md`](../docs/architecture/desktop-product-projection.md)。

## 边界

- `local/` 是 Tauri Local Mode 的 API、composition 和 SQLite persistence。
- `tools/` 包含 Tauri Local Mode 使用的 desktop-specific tools；通过其 registry 注册新 tools，并将 filesystem access 保持在文档规定的 safety boundary 内。
- `app/`、`core/`、`ui/`、`capture/`、`storage/`、`utils/` 属于已废弃的 PySide6 shell，不得作为新 Desktop 功能的 ownership boundary。

不要让 desktop code 依赖 backend internals。对于 text-agent behavior，优先使用 `agent_runtime` 和 `llm_gateway` package protocols，并保留 local configuration/data paths。

## 关键路径

- `local/server.py` — Tauri 启动的 Local API entrypoint。
- `local/composition.py` — Local Mode composition 和 API routes。
- `local/store.py` — Local SQLite persistence。
- `tools/` — Local Mode tools。
- `main.py`、`app/`、`core/`、`capture/`、`storage/`、`ui/`、`utils/` — deprecated PySide6 client。

## 验证

有条件时运行相关 desktop tests。至少在安装 desktop dependencies 后 import 或执行变更模块；不要用 backend startup commands 验证 desktop-only changes。

## 参考

- [根目录 instructions](../AGENTS.md)
- [Agent Runtime](../packages/agent_runtime/AGENTS.md)
- [LLM Gateway](../packages/llm_gateway/AGENTS.md)
- [Desktop Product Projection](../docs/architecture/desktop-product-projection.md)

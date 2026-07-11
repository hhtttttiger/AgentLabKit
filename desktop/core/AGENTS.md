# core — 基础设施

> **定位**：桌面端的基础层。配置管理、Gateway 组装、异步桥接。不依赖任何其他 desktop 模块。

## 职责

- 配置读写（TOML 格式，`~/.config/agentlabkit/desktop.toml`）
- 根据配置创建 GatewayService
- Qt 事件循环与 asyncio 的桥接

## 文件

| 文件 | 说明 |
|------|------|
| `config.py` | `AppConfig` / `LLMConfig` 数据类 + TOML 序列化 |
| `bootstrap.py` | `create_gateway(llm_config)` → `GatewayService` |
| `async_bridge.py` | `run_async(coro, on_result, on_error)` — QThread 中运行 asyncio |

## 依赖方向

```
config.py          ← 无内部依赖（基础层）
bootstrap.py       ← config.py + llm_gateway
async_bridge.py    ← 无内部依赖（仅 PySide6 + asyncio）
```

## 核心接口

```python
# config.py
config = AppConfig.load()    # 从 ~/.config/agentlabkit/desktop.toml 加载
config.save()                # 写回文件

# bootstrap.py
gateway = create_gateway(llm_config)  # → GatewayService

# async_bridge.py
run_async(coro, on_result=fn, on_error=fn, parent=qwidget)
```

## 注意事项

- `config.py` 是整个 desktop 的基础层，**不得依赖**其他 desktop 模块
- `bootstrap.py` 是唯一接触 `llm_gateway` 包的 desktop 文件
- `async_bridge.py` 在独立 QThread 中运行 asyncio 事件循环，通过 Signal 传回结果
- 新增配置项时，同步更新 `LLMConfig`、`AppConfig.load()`、`AppConfig.save()`

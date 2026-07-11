# app — 主控制器

> **定位**：桌面应用的组装层。`DesktopApp` 负责创建所有组件、连接信号槽、管理生命周期。

## 职责

- 创建 QApplication + 所有 UI / 存储 / 工具组件
- 连接信号槽（消息发送 → LLM 调用、截图 → Vision 分析、快捷键 → 切换面板）
- 管理 Gateway 生命周期（初始化 / 配置变更后重建）
- 资源清理（aboutToQuit 回调）

## 文件

| 文件 | 说明 |
|------|------|
| `desktop_app.py` | `DesktopApp` 类 + `main()` 函数 |

## 依赖

依赖 desktop 下所有模块：

```
desktop_app.py
  ├─▶ core.config (AppConfig, CONFIG_FILE)
  ├─▶ core.bootstrap (create_gateway)
  ├─▶ core.async_bridge (run_async)
  ├─▶ ui.pet / ui.tray / ui.chat / ui.settings
  ├─▶ storage.chat_store (ChatStore)
  ├─▶ capture.screen / capture.vision
  ├─▶ utils.hotkey / utils.clipboard
  └─▶ llm_gateway (TextGenerateRequest)
```

## 注意事项

- `DesktopApp` 是**唯一**需要了解所有模块的文件
- 新增模块时，在此注册信号连接和生命周期管理
- `main.py`（根目录）只负责单实例检查，延迟导入 `desktop_app` 避免锁竞争

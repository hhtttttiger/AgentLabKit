# utils — 工具模块

> **定位**：系统级工具。全局快捷键 + 剪贴板监听。可选依赖，优雅降级。

## 职责

- 全局热键监听（系统级，非窗口级）
- 剪贴板内容变化检测

## 文件

| 文件 | 说明 |
|------|------|
| `hotkey.py` | `GlobalHotkey` — Ctrl+Space 全局快捷键（pynput，可选依赖） |
| `clipboard.py` | `ClipboardWatcher` — QTimer 轮询 QClipboard，检测新复制文本 |

## 核心接口

```python
# hotkey.py
hotkey = GlobalHotkey(combo="<ctrl>+<space>", callback=fn)
ok = hotkey.start()       # pynput 不可用时返回 False
hotkey.stop()

# clipboard.py
watcher = ClipboardWatcher(interval_ms=1000)
watcher.text_copied.connect(on_text)  # Signal(str)
watcher.set_enabled(False)            # 暂停监听
watcher.stop()
```

## 可选依赖

- `pynput`：全局快捷键。未安装时 `GlobalHotkey.start()` 返回 False，日志提示
- `QClipboard`：Qt 内置，无额外依赖

## 注意事项

- `hotkey.py` 在后台线程监听键盘事件，回调通过 Qt Signal 安全地传回主线程
- `clipboard.py` 仅在对话面板可见时显示通知，避免打扰用户
- 两个模块都在 `aboutToQuit` 时清理资源

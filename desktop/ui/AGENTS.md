# ui — 界面组件

> **定位**：所有 PySide6 窗口组件。仅依赖 PySide6 和 `core.config`（settings.py），不依赖业务逻辑。

## 职责

- 纯 UI 组件：窗口、布局、样式、交互
- 通过 Qt Signal 向外通信，不直接调用其他模块
- 所有样式内联（QSS 字符串），无外部样式文件

## 文件

| 文件 | 说明 |
|------|------|
| `pet.py` | 桌宠窗口：透明置顶可拖动、4 状态动画（idle/thinking/happy/sleepy）、右键菜单互动 |
| `tray.py` | 系统托盘：图标 + 右键菜单，发射 `show_chat_requested` / `settings_requested` / `quit_requested` |
| `chat.py` | 对话面板：消息气泡（ChatBubble / ImageBubble）、输入框、📎 附件按钮 |
| `settings.py` | 设置面板：提供商预设（OpenAI/Anthropic/DeepSeek/Ollama）、表单、密码显隐 |

## 信号接口

```python
# PetWindow
clicked                    # 点击桌宠

# TrayManager
show_chat_requested        # 请求显示对话
settings_requested         # 请求打开设置
quit_requested             # 请求退出

# ChatPanel
message_sent(str)          # 用户发送文本消息
screenshot_requested       # 请求截图识别
image_selected(str)        # 选择了图片文件路径
```

## 注意事项

- UI 组件**不直接调用** LLM / 存储 / 截图，只发信号
- `settings.py` 是唯一读取 `core.config` 的 UI 文件（用于加载/保存配置）
- 桌宠动画由 QTimer 驱动，800ms 一帧
- 新增 UI 组件时，在 `app/desktop_app.py` 中注册信号连接

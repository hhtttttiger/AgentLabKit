# capture — 截屏 + 图片理解

> **定位**：屏幕截图区域选择 + Vision API 调用。独立于 UI 层，返回 QPixmap 和文本结果。

## 职责

- 全屏截图 + 鼠标框选区域（覆盖层交互）
- 图片编码（QPixmap → base64）
- 调用 OpenAI / Anthropic Vision API 分析图片

## 文件

| 文件 | 说明 |
|------|------|
| `screen.py` | `ScreenOverlay`（全屏覆盖层，鼠标框选）+ `capture_screen_region()` |
| `vision.py` | `analyze_image()` — 直连 Vision API + `pixmap_to_base64()` |

## 核心接口

```python
# screen.py
overlay, pixmap = capture_screen_region()
overlay.region_selected.connect(on_pixmap)   # QPixmap
overlay.region_cancelled.connect(on_cancel)

# vision.py
text = await analyze_image(llm_config, image_b64, prompt, mime_type)
b64 = pixmap_to_base64(pixmap)
```

## 设计决策

- **Vision 直连 API**：llm_gateway 暂不支持多模态输入，因此 vision.py 用 httpx 直接调用 OpenAI/Anthropic
- **自动降级模型**：如果用户配置的模型不支持 vision，自动降级到 gpt-4o-mini / claude-sonnet
- **无 Pillow 依赖**：截屏使用 PySide6 原生 `QScreen.grabWindow()`

## 注意事项

- `ScreenOverlay` 使用 `startSystemMove()` 实现 Wayland 兼容的拖动
- ESC 键取消选区，最小 10px 尺寸防误触
- 截图前需隐藏应用窗口（150ms 延迟确保完全隐藏）

# AgentLabKit 前端设计规范

本文档是 `frontend/admin` Web 客户端与当前 Tauri Desktop 客户端共享的界面设计规范。实现以现有主题 token、共享 UI 组件和桌面壳层样式为准；新增界面应优先复用这些约定。

## 设计范围

- Web 端与当前 Tauri Desktop 端共用 `frontend/admin` 的 React UI、主题 Provider 和 CSS token。
- Tauri Desktop 的入口是 `frontend/admin/src-tauri`。
- `desktop/main.py`、`desktop/app` 等旧 PySide6 外壳已废弃，不属于当前设计系统覆盖范围。

## 主题与全局圆角

界面偏好提供一个全局圆角调试参数，用来观察同一套界面在锋利与圆润之间的视觉变化。

| 项目 | 规范 |
| --- | --- |
| CSS token | `--radius-global` |
| 默认值 | `2px` |
| 调节范围 | `0–20px`，步进 `1px` |
| 设置位置 | 用户菜单 → 界面偏好 → 圆角大小；登录页偏好面板也提供入口 |
| 持久化 | `localStorage`，键名 `agentlabkit-radius` |
| 实时更新 | 修改后立即写入 document root，当前页面无需刷新 |

实现入口：

- [ThemeProvider](frontend/admin/src/shared/theme/providers/ThemeProvider.tsx)
- [RadiusSlider](frontend/admin/src/shared/ui/RadiusSlider.tsx)
- [全局主题样式](frontend/admin/src/index.css)

### 应用规则

以下矩形 UI 应使用 `var(--radius-global)`：

- 按钮、分页按钮和操作入口
- 列表、表格、卡片和工作区横幅外框
- 输入框、下拉框和文本框
- 侧边栏菜单项、图标容器和桌面壳层控件

以下语义形状不应被全局圆角覆盖：

- 圆形头像、状态点和图表标记
- 胶囊标签、状态 Badge 和其他明确表达“全圆”的组件
- 为布局边缘明确要求贴合视口的根容器

新组件如需矩形圆角，应直接引用 `var(--radius-global)` 或使用可被主题 token 覆盖的 `rounded-*` utility；不要重新写死 `border-radius: 2px`、`border-radius: 0` 作为普通控件默认值。

## 组件一致性

- 相同语义的操作使用相同的按钮层级和形状。
- 共享控件放在 `frontend/admin/src/shared/ui`，页面专属布局样式放在所属模块或 `app/shell`。
- 颜色使用语义 token，例如 `--color-primary`、`--color-border-default` 和 `--color-text-secondary`，避免在组件中散落原始颜色值。
- 交互控件必须保留键盘访问、可见焦点、禁用态和可理解的 aria label。
- 圆角变化是主题状态变化，不应通过重新挂载组件或页面刷新实现。

## 验证要求

修改前端设计 token 或共享组件后，在 `frontend/admin` 执行：

```bash
npm run check
npm run test
npm run build
```

视觉验证至少覆盖 Web 与 Tauri Desktop 的首页、列表页、设置面板和表单控件，并检查圆形状态元素与胶囊标签没有被误改成普通圆角。

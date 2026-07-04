# 小屏适配优化设计文档

**日期：** 2026-04-29  
**背景：** 客户主力设备为 1080p 显示器 + Windows 150% DPI 缩放，等效 CSS 视口宽度仅 1280px，导致后台管理页面元素拥挤、表格触发横向滚动。

---

## 问题描述

当前布局在 1280px CSS 视口下的空间消耗：

| 区域 | 宽度 |
|------|------|
| Shell padding × 2 | 36px |
| 侧边栏 | 256px |
| Gap | 14px |
| 内容区 px-8 × 2 | 64px |
| **表格可用宽度** | **≈ 892px** |

Agent 管理页 6 列合计约需 1062px，超出可用宽度 ~170px，触发横向滚动或文字换行。垂直方向，650px 可用高度扣除 header/filter/pagination 后，当前行高 py-4（~72px/行）只能显示约 6 行。

---

## 优化方案：A + B + C

### A — 小屏自动折叠侧边栏

**触发条件：** CSS media query `max-width: 1400px`  
**行为：** 自动为 `AppShell` 根元素追加 `admin-shell--collapsed` class，将侧边栏收缩至 78px 图标模式。

实现位置：`src/styles/index.css`，在现有 `@media` 块中追加：

```css
@media (max-width: 1400px) {
  .admin-shell:not(.admin-shell--force-expanded) {
    grid-template-columns: 78px 1fr;
  }
  .admin-shell:not(.admin-shell--force-expanded) .admin-sidebar {
    padding: 24px 12px 18px;
  }
  .admin-shell:not(.admin-shell--force-expanded) .admin-sidebar__brand-text,
  .admin-shell:not(.admin-shell--force-expanded) .admin-sidebar__link-label {
    opacity: 0;
    max-width: 0;
    pointer-events: none;
  }
  /* ... 其余与 .admin-sidebar--collapsed 一致的规则 */
}
```

**关键约束：**
- 用户手动展开后，`AppShell` 写入 `admin-shell--force-expanded` class 并持久化到 localStorage（key: `ai-admin-sidebar-force-expanded`），优先级高于媒体查询。
- 用户手动折叠后，清除 `force-expanded` flag，恢复媒体查询自动行为。
- `collapsed` state 在 `AppShell` 中已有逻辑，需扩展为区分"用户显式操作"和"自动响应"两种来源。

**释放空间：** 178px 横向空间。

---

### B — 操作列改为 RowActions 下拉菜单

新增共享组件 `src/shared/ui/RowActions.tsx`，提供统一的行操作菜单。

**接口设计：**

```tsx
type RowAction = {
  label: string;
  onClick: () => void;
  variant?: 'default' | 'danger';
};

<RowActions actions={[
  { label: '管理 Prompt 与版本', onClick: () => navigate(...) },
  { label: '编辑定义', onClick: () => setEditingAgentKey(row.agentKey) },
]} />
```

**视觉行为：**
- 触发器：一个 `⋯` 图标按钮（32×32px），hover 时显示边框。
- 菜单：绝对定位浮层，右对齐，`z-index: 50`，点击外部或按 Escape 关闭。
- 菜单项：`variant='danger'` 时文字显示红色。

**应用范围：** 初期仅改 `AgentsPage.tsx` 的操作列，其他列表页（MCP Servers、技能管理、工具管理）在后续视需要跟进，共享同一组件。

**操作列宽度：** 从 ~230px 缩至 40px，释放 ~190px。

---

### C — DataTable 紧凑行高

修改 `src/shared/ui/DataTable.tsx`，将 `td` 的 padding 从 `px-4 py-4` 调整为 `px-4 py-2.5`，表头 `th` 从 `px-4 py-3` 调整为 `px-4 py-2`。

同步调整 `src/shared/ui/FilterToolbar.tsx` 的垂直 padding（如有），与表格视觉密度保持一致。

**效果：** 行高从 ~72px 降至 ~52px，同屏行数从 6 行增至约 8 行。

**兼容性：** AgentPage 操作列改为 `RowActions` 后，单元格高度不再被多按钮撑高，压缩行高才能真正生效。B 和 C 存在顺序依赖，先做 B 再做 C。

---

## 改动范围

| 文件 | 改动类型 |
|------|----------|
| `src/styles/index.css` | 新增 `@media (max-width: 1400px)` 响应式折叠规则 |
| `src/app/shell/AppShell.tsx` | 扩展 collapsed 逻辑，支持 auto-collapse + force-expanded |
| `src/shared/ui/RowActions.tsx` | **新增**，行操作下拉菜单组件 |
| `src/shared/ui/DataTable.tsx` | 调整 td/th padding |
| `src/modules/agent-management/resources/agents/AgentsPage.tsx` | 操作列改用 `RowActions` |

---

## 不在本次范围内

- 其他列表页（MCP Servers、技能管理等）的操作列迁移（可跟进）
- Module header tab 的响应式压缩
- 移动端适配

---

## 验收标准

1. 在浏览器 DevTools 设置视口为 1280×720 时，Agent 管理页无横向滚动条
2. 同屏可见行数 ≥ 8
3. 点击 `⋯` 菜单可正常触发「管理 Prompt 与版本」和「编辑定义」操作
4. 在 1280px 视口下侧边栏自动折叠；用户手动展开后刷新页面仍保持展开
5. 1920px 视口下侧边栏默认展开，行为与改前一致

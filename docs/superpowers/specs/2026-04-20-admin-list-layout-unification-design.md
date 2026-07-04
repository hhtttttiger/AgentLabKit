# Admin List Layout Unification Design

Date: 2026-04-20
Status: Approved for implementation
Scope: Unify page titles, list scrolling behavior, bottom pagination, and refresh actions across all front-end admin management modules.

## Problem

The current admin UI repeats hierarchy and list interactions in a way that makes the management experience feel inconsistent:

- module layout pages already render a top-level module title such as `Agent 管理`
- resource pages render a second large title such as `Agent 定义`
- the result is a stacked two-level title that feels redundant on management pages
- list pages place pagination inside the same scroll flow as the table body
- when rows are long, users lose pagination controls while scrolling
- list pages do not expose a consistent `刷新` action

This problem is not limited to `Agent 管理`. The same structural pattern appears across management-style modules such as:

- `agent-management`
- `model-management`
- `knowledge-base`
- `model-monitoring`
- other admin resource pages that use `PageFrame + FilterToolbar + DataTable + Pagination`

The change must therefore be systemic, not page-specific.

## Goals

- Replace stacked parent/child page headings with a single-line title pattern: `模块 / 页面`
- Keep module context visible without repeating two large headings
- Make paginated list pages scroll only in the data region
- Keep pagination visible at the bottom of the list container
- Add a consistent `刷新` action to list pages
- Apply the pattern across all admin management modules that use the shared list layout model

## Non-Goals

- Redesigning the overall sidebar, shell, or visual theme
- Changing route structure or navigation information architecture
- Redesigning detail pages that are not list-oriented unless they rely on the same header pattern
- Introducing infinite scroll or virtualized table behavior in this iteration

## Design Direction

### Product Context

This UI is an internal admin console. The dominant task is operational management: filtering, checking state, making edits, and recovering from stale data quickly.

The interface should therefore feel:

- precise
- dense but readable
- operational rather than promotional
- stable and repeatable across modules

### Signature Move

Management resource pages use a single command-style heading row:

- `模块名` in subdued emphasis
- `/` as structural separator
- `页面名` in primary emphasis

This preserves location context while removing the feeling of duplicated section headers.

### Defaults To Reject

- stacked large `h1 + h2` titles for management pages
- full-page scrolling for table, pagination, and filters as a single block
- per-page ad hoc refresh placements

## Information Hierarchy

For management list pages, the visual hierarchy becomes:

1. module context and page name in one heading line
2. page actions such as `新建`
3. filter toolbar with `刷新` and `重置`
4. list card containing table body
5. pagination footer fixed to the bottom of the list container

This keeps the user focused on the active resource while preserving module context.

## Layout Model

## 1. Module Layout Header

Module layout headers such as `Agent 管理`, `模型管理`, and `知识库` continue to exist at the module layout level.

They keep:

- the module label
- tab navigation
- the existing shell-level framing

They should stop competing visually with a second large content title below.

## 2. Page Header

`PageFrame` becomes responsible for rendering a compact management-page heading model.

For management pages, the title area should support:

- `sectionTitle`: the module name, for example `Agent 管理`
- `title`: the resource or tab page name, for example `Agent 定义`
- optional description
- action area on the right

Rendered result:

- `Agent 管理 / Agent 定义`

Visual rules:

- module name uses smaller or muted emphasis
- slash is a neutral separator
- page title remains the strongest text
- description stays below the line if present

This keeps one clear heading without losing context.

## 3. List Container

Paginated list pages use a three-part layout inside the content region:

- filter toolbar block
- scrollable data block
- fixed footer pagination block

Only the data block scrolls vertically.

Pagination must remain anchored at the bottom of the list container so that:

- users always see current page position
- page navigation remains reachable after scrolling long rows
- the page feels like a control surface rather than a static document

## 4. Refresh Action

All management list pages expose a `刷新` button in the filter/action strip.

Behavior:

- re-fetch the current query
- preserve filters
- preserve current page
- preserve current tab or module context
- do not reset forms or clear local filters

Placement:

- right-aligned within the filter toolbar action area
- visually grouped with list operations, not with primary creation actions

## Component Strategy

## Shared Components To Extend

### `PageFrame`

Extend `PageFrame` to support a management-title mode:

- `sectionTitle`
- existing `title`
- optional `description`
- actions
- optional supporting content

It should render the combined heading cleanly without forcing every page to hand-build the same markup.

### List Page Shell

Introduce a shared list-page structure for admin resource pages. This can be either:

- a new reusable component such as `ManagementListFrame`
- or a reusable composition pattern built from `PageFrame`, `FilterToolbar`, `DataTable`, and `Pagination`

The preferred outcome is a single shared abstraction because the behavior is repeating across modules.

Responsibilities:

- own vertical flex layout
- reserve footer space for pagination
- constrain table scrolling to the middle region
- accept filter toolbar, table content, and pagination as slots
- optionally expose a standard refresh action input

### `Pagination`

`Pagination` stays visually lightweight, but it should be used inside a non-scrolling footer region.

The component itself does not need to become globally sticky to the viewport. The requirement is footer anchoring within the list container.

### `DataTable`

`DataTable` should remain focused on tabular rendering. The scroll containment should be handled by the list shell rather than by table internals alone.

If needed, `DataTable` can accept class hooks for height and body overflow, but it should not absorb pagination responsibilities.

## Application Scope

The implementation should update all management-style pages that follow the standard admin list pattern, including at least:

- `agent-management/resources/agents/AgentsPage.tsx`
- `agent-management/resources/mcp-servers/McpServersPage.tsx`
- `agent-management/resources/skills/SkillsPage.tsx`
- `agent-management/resources/tools/ToolsPage.tsx`
- `model-management/resources/*` list pages
- `knowledge-base` list-style pages that use shared pagination
- `model-monitoring/resources/*` list pages

Pages that are overview dashboards or pure detail pages should only adopt the unified title pattern if they use the same management-page frame. They do not need forced pagination changes when no paginated list exists.

## Interaction Details

## Refresh

- Disabled while the underlying list query is actively refetching if the page already exposes a loading state
- Uses the same query source as the page’s existing data hook
- Error handling remains with the page’s current inline error message

## Pagination

- Previous/next controls stay in the footer
- Current page summary stays visible even while table content scrolls
- Empty states still render in the data region

## Table Scrolling

- Header and filters stay above the scroll region
- Pagination stays below the scroll region
- Row content scrolls within the bounded data area

## Responsive Behavior

Desktop:

- combined title and page actions stay on the same row when space allows
- filter controls wrap naturally
- pagination footer keeps left summary and right controls

Tablet / narrow laptop:

- title row can wrap to two lines
- actions move below the title if needed
- filter toolbar wraps to multiple rows

Mobile:

- combined title remains readable as one semantic heading
- action buttons stack or wrap cleanly
- pagination footer can collapse into a vertical layout if width is tight

## Accessibility

- The combined title still renders as a single semantic page heading
- Focus order remains: page actions -> filters -> table -> pagination
- Refresh button has an explicit text label and must not be icon-only
- Sticky or anchored footer must not obscure focused controls or table rows
- Keyboard users must be able to reach pagination without scrolling the entire page container unexpectedly

## Error Handling

- Existing inline error surfaces remain the source of truth for load failures
- Refresh does not introduce a second error presentation model
- Empty states remain inside the data region and should not collapse the footer pattern unexpectedly

## Testing Requirements

Minimum automated coverage:

- shared layout/component tests for combined title rendering
- list-page tests verifying `刷新` is rendered where expected
- pagination rendering tests that still show page summary and controls after layout refactor
- at least one representative page test from each major management module touched by the refactor

Minimum manual verification:

1. Open `Agent 管理 -> Agent 定义`
2. Confirm title renders as `Agent 管理 / Agent 定义`
3. Scroll the list and confirm only the table region scrolls
4. Confirm pagination stays fixed at the bottom of the list card
5. Click `刷新` and confirm current filters and page are preserved
6. Repeat the same checks on a model-management page and a knowledge-base page

## Risks

### Risk: overfitting to one page

If the implementation is based only on `AgentsPage`, other modules will drift again.

Mitigation:

- implement the pattern through shared layout primitives
- migrate all management pages that use the common list structure

### Risk: scroll bugs from nested flex containers

Admin pages already use nested `h-full`, `flex`, and `overflow` containers.

Mitigation:

- keep one explicit scroll owner for the data region
- verify `min-h-0` placement in shared containers
- avoid adding competing `overflow-y-auto` wrappers

### Risk: responsive header collisions

Combining module and page titles with actions may crowd smaller widths.

Mitigation:

- allow the heading row to wrap
- keep module label visually quieter than page title
- test at narrow widths before completion

## Acceptance Criteria

The design is complete when all of the following are true:

1. Management pages no longer show stacked redundant module/page titles.
2. Combined headings render in the form `模块 / 页面`.
3. Paginated list pages scroll only in the data region.
4. Pagination stays anchored at the bottom of the list container.
5. Management list pages expose a consistent `刷新` action.
6. The pattern is implemented across the admin management modules, not just the agent page.

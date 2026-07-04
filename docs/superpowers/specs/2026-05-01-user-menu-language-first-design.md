# User Menu and Login Preferences Design

Date: 2026-05-01
Status: Approved for implementation
Scope: Reduce clutter in the top-right user menu by adopting a two-level menu model where language selection remains a first-level, icon-led entry and visual preferences move into a secondary settings layer, and extend login-page pre-auth preferences with visible language and accent switching.

## Problem

The current `UserMenu` mixes several different kinds of actions into one small dropdown:

- user identity
- logout
- language switching
- theme toggle
- accent selection
- motion toggle
- zoom controls

This creates three UX problems:

1. the menu feels crowded and over-functional for a top-right account trigger
2. account actions and UI preferences are mixed together without clear hierarchy
3. language switching is visually available today, but any future simplification risks burying it in a place that non-Chinese speakers may struggle to find after landing on a Chinese UI

The redesign must reduce clutter without sacrificing recoverability for language switching.

The current login page has a different but related limitation:

- it already exposes a bottom `ThemeToggle`
- but it does not expose login-page language switching
- and it does not expose accent switching before authentication

This means the signed-out experience still lacks the same recoverability and personalization controls we want in the authenticated shell.

## Goals

- Make the top-right menu feel lighter and easier to scan
- Separate account actions from interface preferences
- Keep language switching discoverable even when the current UI language is unreadable to the user
- Preserve the existing preference capabilities
- Keep the interaction model compact enough for an admin console toolbar
- Add pre-auth language and accent switching to the login page without distracting from the sign-in task

## Non-Goals

- Redesigning the global app shell or sidebar
- Removing existing preference capabilities such as accent, motion, or zoom
- Moving all preferences into a full-page settings module
- Changing locale persistence, theme persistence, or existing preference storage keys
- Redesigning the login form itself beyond the bottom preference area

## Design Direction

### Recommended Pattern

Adopt a **language-first hybrid of the two-level menu**:

- first-level menu remains the primary user/account dropdown
- language is elevated to a first-level item with a strong icon
- visual preferences move behind a dedicated second-level menu entry

This preserves the compactness of the double-layer approach while protecting language switching as a recovery action.

For the login page, adopt a matching **pre-auth preferences bar**:

- place it inside the login card footer
- keep login form content as the primary visual focus
- expose language and accent directly before login
- retain theme switching in the same footer area rather than as a separate lone control

### First-Level Menu Structure

The first-level user menu should contain exactly four entries:

1. `账户信息` or account summary
2. `Language` entry with a `Languages`/globe-style icon
3. `界面偏好` entry that opens a second-level preferences panel
4. `退出登录`

This keeps the menu small, predictable, and semantically clean.

### Second-Level Preferences Structure

The second-level preferences panel contains UI personalization controls only:

- theme
- accent color
- motion
- zoom

Language is explicitly excluded from this panel.

## Information Architecture

### 1. Account Layer

The user trigger represents identity and session actions.

It should primarily answer:

- who is signed in
- where account-related actions live
- how to exit the session

It should no longer serve as a flat list of every preference control.

### 2. Language as a Recovery Layer

Language selection is a special case. Unlike accent or motion, it is not just a preference; it is also a **navigation recovery mechanism**.

If a user lands on an unreadable locale, they still need a reliable way to recover. For that reason:

- language must stay at the first level
- the item must be identifiable by icon, not only by translated text
- the label should prefer a stable cross-lingual pattern such as `Language` or an icon + short locale value

This rule matters more than keeping all preferences grouped together.

### 3. Preferences as a Secondary Layer

Visual customization belongs in a second layer because:

- it is lower frequency than language recovery
- it benefits from grouping
- it avoids flooding the primary menu with controls and inline widgets

This layer can be rendered as either:

- a submenu anchored to the dropdown
- or a compact secondary panel replacing the current dropdown body

The key requirement is that the first-level menu remains short and readable.

## Interaction Model

## 1. User Trigger

The top-right trigger continues to show user initials/avatar and optional name.

No change is required to the trigger’s placement in `AppShell`.

## 2. First-Level Menu Behavior

The first-level menu opens as the default dropdown view.

Recommended item behavior:

- **Account**: static summary row or navigable profile entry
- **Language**: opens an inline lightweight language chooser from the first level
- **Preferences**: opens the second-level preferences view
- **Logout**: remains a bottom danger action

The first view should not contain embedded accent dots, sliders, or grouped button clusters.

## 3. Language Entry Behavior

Language should be exposed as a first-level, icon-led row.

Recommended visual treatment:

- `Languages` or globe icon on the left
- stable label that remains recognizable across locales
- current locale value shown on the right, for example `中文 / EN`

Recommended interaction:

- clicking the row opens a small inline chooser or adjacent subpanel
- chooser shows only supported locales
- chooser remains simpler than a generic settings screen

Language should feel fast to recover, not buried in settings.

## 4. Preferences Entry Behavior

The `界面偏好` entry opens the second-level menu.

The second level should group controls in a clean vertical list, for example:

- theme mode
- accent color
- motion
- zoom

These controls may still use richer widgets inside the second layer because they are no longer competing for attention in the primary menu.

## 5. Logout Behavior

Logout remains at the bottom and visually separated as the irreversible session action.

This part of the current menu model is already correct and should be preserved.

## Login Page Model

### 1. Placement

The login page should expose pre-auth preferences inside the login card, at the bottom, below the submit button.

This area replaces the current single `ThemeToggle` row with a compact, unified preferences bar.

### 2. Contents

The login-page preferences bar should contain:

- language switcher
- accent switcher
- theme toggle

This creates parity with the authenticated experience while staying intentionally smaller than the signed-in preferences menu.

### 3. Interaction Principle

The login form remains the main task surface.

The footer bar should therefore feel:

- secondary in emphasis
- immediately available
- compact and low-noise

It should not look like a second form or a toolbar competing with the submit action.

### 4. Language Behavior on Login Page

Language must be available before authentication for the same recovery reason described in the user menu:

- a user may land on an unreadable locale before signing in
- they need a quick way to recover without guessing through the form

Recommended treatment:

- icon-led `Language` entry or compact control
- visible in the card footer
- limited to supported locales only

### 5. Accent Behavior on Login Page

Accent switching should also be available before authentication because the login card already uses accent-driven visual treatment.

Recommended treatment:

- small 3-5 option swatch group
- visually compact presentation
- reuse the existing accent persistence behavior

Accent selection is a personalization enhancement, not a recovery feature, so it should remain lighter in emphasis than language.

### 6. Theme Behavior on Login Page

The current bottom `ThemeToggle` should be kept, but absorbed into the unified footer preferences bar.

This avoids introducing yet another isolated control while preserving the existing capability.

## Visual Hierarchy

- first-level rows should scan as simple menu actions, not as a mixed settings form
- language should have the strongest discoverability after account summary
- preferences should communicate “more settings live here” without exposing all controls immediately
- logout should remain isolated in a danger-styled zone

The overall result should feel like a focused account menu rather than a compressed settings drawer.

On the login page, the same principle becomes: a focused sign-in card with a lightweight preference footer rather than scattered independent controls.

## Accessibility and Internationalization Notes

- The language row must remain discoverable through iconography and accessible labeling
- The icon alone is not sufficient for assistive technology; keep a clear text label and aria label
- Locale options should continue to use the existing `useAdminLocale()` behavior and persistence
- Avoid relying on translated-only labels for the recovery entry; the row should remain recognizable even when the current language is unfamiliar
- Login-page language switching should follow the same persistence behavior so the chosen locale carries into the rest of the experience

## Component Strategy

### Existing Pieces To Reuse

- `UserMenu.tsx` remains the orchestration component
- `LanguagePicker.tsx` should be reused for the language chooser behavior
- `ThemeToggle`, `AccentPicker`, `ZoomSlider`, and motion toggle logic should move behind the preferences layer rather than remaining in the first view
- `LoginPage.tsx` should replace the current lone `ThemeToggle` footer with a compact pre-auth preferences bar

### Likely Structural Change

`UserMenu` should move from a single flat dropdown to a small view-state model:

- `root`
- `language`
- `preferences`

This enables compact transitions without introducing a larger settings page.

For login, no second-level navigation is required. The preference area can stay as a single compact footer row because only language, accent, and theme are exposed before login.

## Acceptance Criteria

- Opening the user menu shows a short first-level menu rather than the current dense control list
- Language is visible from the first-level menu and identifiable by icon
- Theme, accent, motion, and zoom are no longer rendered directly in the first-level view
- A user who cannot read Chinese can still find language switching from the top-right menu
- Existing preference persistence continues to work
- The login page shows language, accent, and theme controls inside the card footer
- The login form remains visually dominant after adding the footer preferences bar

## Open Decisions Resolved

- **Chosen baseline:** double-layer menu
- **Applied adjustment:** language promoted to first-level visibility
- **Login-page adjustment:** add a compact in-card footer bar for language, accent, and theme
- **Rejected alternative:** placing language inside the preferences submenu
- **Rejected alternative:** keeping all preferences flat in the primary menu

## Testing Expectations

Implementation should verify at least:

- first-level menu content and ordering
- language entry discoverability and switching behavior
- second-level preferences navigation
- preserved persistence for locale, theme, accent, motion, and zoom
- logout path still works from the revised structure
- login-page language switching before authentication
- login-page accent switching before authentication
- login-page theme toggle still works from the new footer bar

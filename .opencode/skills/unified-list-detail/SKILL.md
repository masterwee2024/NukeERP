---
name: unified-list-detail
description: >-
  pyERP unified list+detail CRUD pattern. Every admin/master-data page uses a
  single component that renders as a split-pane on desktop (list left, detail
  right) and a full-page list-then-detail on mobile with a back button. Fused
  into the Dynamic Page Config system so no per-page code is needed for
  standard CRUD. Custom actions extend via action slots.
license: MIT
compatibility: opencode
---

# Unified List-Detail CRUD Pattern

## Core Concept

Every page is **list + detail**. Desktop shows both side-by-side in a split-pane. Mobile shows the list first; tapping a row navigates to a full-page detail view with a ← Back button to return to the list.

**One component renders everywhere** — the same `viewContent` (read-only view, edit form, create form) is used for both mobile and desktop. The layout shell (`FormPageLayout`) handles the arrangement.

## Architecture

```
DynamicListDetailPage  (one component, all pages)
├── useIsMobile()
├── FormPageLayout (30/70 resizable split)
│   ├── left:  CardList (toCard → compact 2-row cards)
│   └── right: DetailView
│               ├── viewing  → renderDetail(record)
│               ├── editing  → renderForm(record)
│               ├── creating → renderForm(null)
│               ├── idle     → "Select a record"
│               └── actionSlots
│                   ├── detailHeader  → extra buttons
│                   ├── betweenSections → sub-lists
│                   └── detailFooter  → extra forms
└── Mobile: card list full-page → tap card → detail full-page with ← Back
```

## Breakpoint Behaviour

| Viewport | List | Detail/Form |
|----------|------|-------------|
| >1024px (wide) | `FormPageLayout` left panel (default 30%, drag-resizable 20-80%) | Right panel (default 70%) with drag divider |
| 768-1023px (tablet) | Full-width stacked | Below the list |
| <768px (mobile) | Full-page list (cards) | Full-page detail with ← Back header |

## Shared Components

### `useIsMobile()` / `useIsWide()`
- **Location**: `frontend/src/hooks/useIsMobile.ts`, `frontend/src/hooks/useIsWide.ts`
- Simple `window.matchMedia("(max-width: 767px)")` listeners
- Return boolean — used for navigation layout and button styling

### List Cards (standard)
Cards replace tables for all viewports. Every list is a vertical stack of compact 2-row cards:
- **Row 1**: Entity name/label (left) · Status badge or key metric (right)
- **Row 2**: Detail info (type, identifier, badges) separated by `|` pipes
- Clicking a card opens the detail view
- Cards use `cursor-pointer rounded-lg border border-secondary-200 bg-white p-3`

### `AccordionSection`
- **Location**: `frontend/src/components/shared/AccordionSection.tsx`
- Controlled mode: `isOpen` prop + `onToggle` callback
- Auto-collapse: only one section open at a time
- Uses pyERP color tokens (`secondary-*`, `primary-*`)

### `FormPageLayout`
- **Location**: `frontend/src/components/shared/FormPageLayout.tsx`
- Props: `leftPanel: { id, label, content }`, `rightPanel: { id, label, content }`
- Desktop: flexbox split-pane with **drag-resizable divider**. Default **30% left / 70% right**, clamped 20-80%.
- Divider: `w-1.5 cursor-col-resize bg-secondary-200 hover:bg-primary-400`, tracks `mousedown`/`mousemove`/`mouseup`
- Tablet: stacked `space-y-4` (no split)
- The same component is used by every page — no per-page split logic needed

### `DynamicDetailView`
- **Location**: `frontend/src/components/DynamicDetailView.tsx`
- Renders a page config's fields as read-only (viewing) or editable (creating/editing)
- Groups fields by `section` into `AccordionSection` components
- Handles save, cancel, optimistic locking

### `DynamicListDetailPage`
- **Location**: `frontend/src/components/DynamicListDetailPage.tsx`
- Orchestrator: loads page config, wires list selection to detail view
- Manages state: `viewing`, `editing`, `showForm`, `activeSection`, navigation

## Integration with Page Config

The standard case uses the existing `PageConfig` + `PageConfigField` system:

- `PageConfig.api_endpoint` → detail fetch/update URL
- `PageConfigField.section` → group fields into `AccordionSection` panels
- `PageConfigField.field_type` → render appropriate readonly or form input
- `PageConfig.actions` → derive available CRUD operations

**No schema changes needed** — the existing config fields already carry enough metadata.

## Custom Actions & Non-Standard Pages

Some pages need actions beyond standard CRUD (deactivate/reactivate, password reset, sub-list detail, diff view). These pages should:

1. **Use `FormPageLayout` + `AccordionSection`** — same layout shell and card pattern
2. **Adhere to the breakpoint behaviour** — desktop split, tablet stacked, mobile full-page
3. **Add custom actions as buttons** in the right panel header (outside AccordionSection)
4. **Use `useConfirm()`** for all destructive actions
5. **Delegate to `DynamicListDetailPage` for standard CRUD** — only custom-write sections that differ

### Custom Action Slots

| Slot | Location | Used for |
|------|----------|----------|
| Detail header | Above AccordionSection | Edit, Delete, Deactivate, Approve |
| Between sections | Between AccordionSections | Sub-lists (company assignments, roles) |
| Field replacement | Inside AccordionSection | Password reset inline, diff view |

## When to Use Each Approach

| Scenario | Approach |
|----------|----------|
| Read-only list + detail (e.g. audit log) | `DynamicListDetailPage` with `renderDetail` only |
| Standard CRUD (create, edit, delete, list) | `DynamicListDetailPage` with `renderForm` — no custom code needed |
| Standard CRUD + 1-2 extra buttons | `DynamicListDetailPage` with `actionSlots.detailHeader` |
| Sub-list within detail (e.g. companies under a policy) | `DynamicListDetailPage` with `actionSlots.betweenSections` |
| Non-standard field interactions (e.g. password reset) | `DynamicListDetailPage` with `actionSlots.detailFooter` |

## Shared Components

### `DynamicListDetailPage`
- **Location**: `frontend/src/components/shared/DynamicListDetailPage.tsx`
- Universal wrapper for the unified list-detail pattern
- Provides split-pane shell (`FormPageLayout` on desktop), mobile full-page navigation with ← Back
- Props:
  - `title`, `records`, `isLoading` — list data
  - `toCard` — converts record to `{ id, label, sublabel?, badge?, meta? }` for card rendering
  - `renderDetail` — renders the read-only view for a record
  - `renderForm` — renders the create/edit form
  - `onCreate`, `onEdit`, `onDelete` — CRUD action handlers
  - `actionSlots.detailHeader` — extra buttons in the detail header
  - `actionSlots.betweenSections` — custom content between AccordionSections (e.g. sub-lists)
  - `actionSlots.detailFooter` — content at the bottom of the detail view
  - `onSelect`, `onViewStateChange` — external state control
- **Always use this for any new admin CRUD page**

### Action Slots Pattern
Custom actions are passed as render props rather than extending the base component:

```tsx
<DynamicListDetailPage<User>
  title="Users"
  records={users}
  isLoading={isLoading}
  toCard={(user) => ({ id: user.id, label: user.full_name, badge: {...} })}
  renderDetail={(user) => <UserDetailView user={user} />}
  renderForm={(user) => <UserForm user={user} roles={roles} />}
  onCreate={() => initCreateForm()}
  onEdit={(user) => initEditForm(user)}
  onDelete={(user) => handleDelete(user)}
  actionSlots={{
    detailHeader: (user, refresh) => (
      <DeactivateButton user={user} onDone={refresh} />
    ),
    detailFooter: (user) => (
      <PasswordResetForm user={user} />
    ),
  }}
/>
```

## Implementation Checklist

When building or modifying a page to use this pattern:

- [ ] Uses `DynamicListDetailPage` wrapper — no custom page component needed
- [ ] For standard CRUD: only pass `toCard`, `renderDetail`, `renderForm` and action handlers
- [ ] For custom actions: use `actionSlots` instead of custom page wrappers
- [ ] List uses `toCard` for 2-row compact card layout
- [ ] `useConfirm()` on all create, update, delete actions handled by `DynamicListDetailPage`
- [ ] No `hover:` background on cards (only `cursor-pointer`)
- [ ] No hardcoded Tailwind colors — use pyERP theme tokens (`primary-*`, `secondary-*`, etc.)

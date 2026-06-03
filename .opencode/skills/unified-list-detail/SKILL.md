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
DynamicListDetailPage (configKey="admin.users")
├── usePageConfig(configKey) → fetches PageConfig + PageConfigFields from DB
├── useQuery(config.api_endpoint) → fetches records from API
├── CardList (auto-derived from PageConfigField.is_column)
├── FormPageLayout (30/70 resizable split)
│   ├── left:  Card list
│   └── right: DetailView
│               ├── viewing  → DynamicDetailPage (fields from config)
│               ├── editing  → DynamicFormPage (fields from config)
│               ├── creating → DynamicFormPage (fields from config)
│               ├── idle     → "Select a record"
│               └── actionSlots
│                   ├── detailHeader  → extra buttons (deactivate/reactivate)
│                   ├── betweenSections → sub-lists (company assignments)
│                   └── detailFooter  → extra forms (password reset)
└── Mobile: card list full-page → tap → detail full-page with ← Back
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
| Standard CRUD (create, edit, delete, list) | `DynamicListDetailPage` with `configKey` — zero code |
| Standard CRUD + custom action buttons | `DynamicListDetailPage` with `configKey` + `actionSlots` |
| Read-only (e.g. audit log) | `DynamicListDetailPage` with `configKey` + `actionSlots.betweenSections` |
| Singleton form (not list-detail) | Standalone page (e.g. `EmailSettingsPage`) |

## Shared Components

### `DynamicListDetailPage`
- **Location**: `frontend/src/components/shared/DynamicListDetailPage.tsx`
- **The single component for all admin CRUD pages.** Two patterns:

  **Standard CRUD** — add a page config record + one route line. Zero React code:
  ```tsx
  <Route path="companies" element={<DynamicListDetailPage configKey="admin.companies" />} />
  ```

  **With custom action slots** — import the page component (e.g. `UserManagementPage`) which wraps `DynamicListDetailPage`:
  ```tsx
  // UserManagementPage.tsx
  export default function UserManagementPage() {
    return (
      <DynamicListDetailPage
        configKey="admin.users"
        actionSlots={{
          detailHeader: (record) => <DeactivateButton record={record} />,
          detailFooter: (record) => <PasswordResetForm record={record} />,
        }}
      />
    );
  }
  ```

- Props: `configKey` (required), `title` (optional override), `actionSlots`
- Automatically fetches page config from DB, renders list/detail/form
- Edit/Delete buttons shown only if page config has matching actions
- Desktop: split-pane via `FormPageLayout` (30/70 resizable)
- Mobile: full-page list → tap → full-page detail with ← Back
- **Always use this component. No exceptions.**

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

When building a new admin CRUD page:

- [ ] Seed a `PageConfig` record (via `seed_page_configs` or page builder UI)
- [ ] Add a route in `App.tsx`: `<Route path="..." element={<DynamicListDetailPage configKey="..." />} />`
- [ ] For custom actions: create a wrapper component with `actionSlots`
- [ ] `useConfirm()` on all destructive actions
- [ ] No hardcoded Tailwind colors — use pyERP theme tokens (`primary-*`, `secondary-*`, etc.)

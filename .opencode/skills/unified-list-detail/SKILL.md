---
name: unified-list-detail
description: >-
  pyERP unified list+detail CRUD pattern. Every admin/master-data page uses a
  single `DynamicListDetailPage` with `configKey` — fetches `PageConfig` +
  `PageConfigField` from DB, renders card list + detail/form. Custom actions
  extend via `actionSlots`. Custom fields stored in `custom_fields` JSONB.
license: MIT
compatibility: opencode
---

# Unified List-Detail CRUD Pattern

## Core Concept

Every page is **list + detail**. Desktop shows both side-by-side in a split-pane (30/70 resizable). Mobile shows the list first; tapping a row navigates to a full-page detail view with a ← Back button.

**One component renders all pages** — `DynamicListDetailPage` with a `configKey` pointing to a `PageConfig` record in the database.

## Architecture

```
DynamicListDetailPage (configKey="admin.users")
├── usePageConfig(configKey) → fetches PageConfig + PageConfigFields from DB
├── useQuery(api_endpoint) → fetches records from API, flattens custom_fields
├── CardList (auto-derived from PageConfigField.is_column)
├── FormPageLayout (30/70 resizable split)
│   ├── left:  Card list (2-row cards: label + meta[])
│   └── right: DetailView
│               ├── viewing  → DynamicDetailPage (fields from config)
│               ├── editing  → DynamicFormPage (fields from config)
│               ├── creating → DynamicFormPage (fields from config)
│               ├── idle     → "Select a record"
│               └── actionSlots
│                   ├── detailHeader  → extra buttons (deactivate/reactivate)
│                   ├── betweenSections → sub-lists (company assignments, diff)
│                   └── detailFooter  → extra forms (password reset)
└── Mobile: card list full-page → tap → detail full-page with ← Back
```

## List Cards

Every list is a vertical stack of compact 2-row cards:

- **Row 1**: First column field value (entity name/label)
- **Row 2**: Remaining column fields separated by `|` pipes. Badge-type fields render as colored badges.

Cards use `cursor-pointer rounded-lg border border-secondary-200 bg-white p-3`.

## Custom Fields (via JSONB)

All models inherit `custom_fields` JSONB from `ConcurrencyModel` (`CustomFieldsMixin`).

**Storage**: Unknown field names in API payloads route to `custom_fields` automatically via `model.set_field()` / `__init__` override.

**Frontend merge**: `DynamicListDetailPage` flattens `custom_fields` into each record on fetch — form/detail components see a flat object and never know which fields are custom.

**Field management**: Use the **Field Customizer** at Administration → Field Customizer. Form-based editor: select a page → add/edit/delete fields. Custom fields support types: text, number, decimal, date, datetime, select, multi_select, checkbox, toggle, textarea, email.

## Breakpoint Behaviour

| Viewport | List | Detail/Form |
|----------|------|-------------|
| >1024px (wide) | `FormPageLayout` left panel (default 30%, drag-resizable 20-80%) | Right panel (default 70%) with drag divider |
| 768-1023px (tablet) | Full-width stacked | Below the list |
| <768px (mobile) | Full-page list (cards) | Full-page detail with ← Back header |

## Shared Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `DynamicListDetailPage` | `components/shared/DynamicListDetailPage.tsx` | Main orchestrator — **use this for every admin page** |
| `DynamicFormPage` | `components/dynamic/DynamicFormPage.tsx` | Renders create/edit form from config |
| `DynamicDetailPage` | `components/dynamic/DynamicDetailPage.tsx` | Renders read-only detail from config |
| `FormPageLayout` | `components/shared/FormPageLayout.tsx` | Desktop split-pane (30/70 resizable) |
| `AccordionSection` | `components/shared/AccordionSection.tsx` | Collapsible section for detail views |

## When to Use Each Approach

| Scenario | Approach |
|----------|----------|
| Standard CRUD (create, edit, delete, list) | `DynamicListDetailPage` with `configKey` — zero code |
| Standard CRUD + custom action buttons | `DynamicListDetailPage` with `configKey` + `actionSlots` |
| Read-only (e.g. audit log) | `DynamicListDetailPage` with `configKey` + `actionSlots.betweenSections` |
| Singleton form (not list-detail) | Standalone page (e.g. `EmailSettingsPage`) |
| Add custom fields | Field Customizer UI — no code changes needed |

## Action Slots Pattern

Custom actions are passed as render props rather than extending the base component:

```tsx
<DynamicListDetailPage
  configKey="admin.users"
  actionSlots={{
    detailHeader: (record, refresh) => (
      <DeactivateButton record={record} onDone={refresh} />
    ),
    detailFooter: (record) => (
      <PasswordResetForm record={record} />
    ),
  }}
/>
```

| Slot | Signature | Used for |
|------|-----------|----------|
| `detailHeader` | `(record, refresh) => ReactNode` | Edit, Delete, Deactivate, Reactivate buttons |
| `betweenSections` | `(record) => ReactNode` | Sub-lists (company assignments, change diffs) |
| `detailFooter` | `(record) => ReactNode` | Extra forms (password reset) |

## Implementation Checklist

When building a new admin CRUD page:

- [ ] Seed a `PageConfig` record (via seed script or API)
- [ ] Add a route: `<Route path="..." element={<DynamicListDetailPage configKey="..." />} />`
- [ ] For custom actions: create a wrapper component with `actionSlots`
- [ ] `useConfirm()` on all destructive actions
- [ ] No hardcoded Tailwind colors — use pyERP theme tokens
- [ ] Custom fields need no extra work — they're stored in JSONB, rendered from config

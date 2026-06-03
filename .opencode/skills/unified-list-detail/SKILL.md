---
name: unified-list-detail
description: >-
  pyERP unified list+detail CRUD pattern. Every admin/master-data page uses a
  single component that renders as a split-pane on desktop (list left, detail
  right) and a full-page list-then-detail on mobile with a back button. Fused
  into the Dynamic Page Config system so no per-page code is needed.
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
├── FormPageLayout
│   ├── left:  DynamicList (table, row click → select)
│   └── right: DynamicDetailView
│               ├── viewing  → AccordionSection(s) + Edit button
│               ├── editing  → form with AccordionSection(s)
│               ├── creating → empty form with AccordionSection(s)
│               └── idle     → "Select a record" message
└── Mobile: list full-page → tap row → detail full-page with ← Back
```

## Breakpoint Behaviour

| Viewport | List | Detail/Form |
|----------|------|-------------|
| >1024px (wide) | `FormPageLayout` left panel (resizable grid `1fr 1fr`) | Right panel |
| 768-1023px (tablet) | Full-width stacked | Below the list |
| <768px (mobile) | Full-page list | Full-page detail with ← Back header |

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
- Wide: CSS grid `grid-cols-2`
- Tablet: stacked `grid-cols-1`
- Mobile: hidden layout logic (page handles full-screen switching)

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

The pattern uses the existing `PageConfig` + `PageConfigField` system:

- `PageConfig.api_endpoint` → detail fetch/update URL
- `PageConfigField.section` → group fields into `AccordionSection` panels
- `PageConfigField.field_type` → render appropriate readonly or form input
- `PageConfig.actions` → derive available CRUD operations

**No schema changes needed** — the existing config fields already carry enough metadata.

## CRUD Actions Convention

| Action | Desktop | Mobile | Confirm? |
|--------|---------|--------|----------|
| Add new | Text button "+ Add" | `+` icon button | yes (`warning`) |
| Select row | Click → right panel detail | Click → navigate to detail page | no |
| Edit | Text "Edit" button in detail | Pencil icon button in detail | no (form shown) |
| Save | Text "Save" button | Text "Save" button | yes (`warning`) on create |
| Delete | Text "Delete" button in detail | Trash icon button in detail | yes (`danger`) |
| Back | N/A (split-pane) | ← Back header button | no |

## Implementation Checklist

When building or modifying a page to use this pattern:

- [ ] Uses `DynamicListDetailPage` wrapper — no custom page component needed
- [ ] Page config record exists with proper `api_endpoint` and `fields`
- [ ] Fields are grouped via `section` for AccordionSection layout
- [ ] `useConfirm()` on all create, update, delete actions
- [ ] Cards (not tables) for list view — 2-row compact layout
- [ ] No `hover:` background on cards (only `cursor-pointer`)
- [ ] No hardcoded Tailwind colors — use pyERP theme tokens (`primary-*`, `secondary-*`, etc.)

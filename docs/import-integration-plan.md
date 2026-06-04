# Import Integration Plan — DynamicListDetailPage

## Goal
Make CSV import a built-in feature of every admin CRUD page rendered by `DynamicListDetailPage`.

## Current Problem
- ImportPage is a standalone route — each entity needs its own import page
- New admin UIs use `DynamicListDetailPage` with a `configKey` — but no import capability
- No standard way for any entity to get CSV import

## Solution
Add an `enableImport` prop to `DynamicListDetailPage`. When `true`, an **Import** button appears in the list header alongside **+ New**. Clicking it opens an `ImportModal` that handles the full import flow.

## Changes

### 1. Backend — Template lookup by page_key
New endpoint: `GET /api/v1/core/import/templates/by-page/{page_key}/`

Maps `page_key` → `PageConfig.entity_model` → reverse lookup in import_template definitions → return the matching template.

### 2. Frontend — `ImportModal` component
New file: `frontend/src/components/shared/ImportModal.tsx`
- Overlay modal (desktop) / full-screen (mobile)
- Steps: select file → auto-detect template → upload → validate → import → done
- Auto-map: calls `GET /import/templates/by-page/{page_key}/` to find matching template
- On success: calls `onImportComplete()` to refresh the list

### 3. Frontend — `enableImport` prop on DynamicListDetailPage
- New optional prop: `enableImport?: boolean`
- When true, renders Import button in the list header
- Renders ImportModal when button is clicked, passing the configKey
- Modal appears as an overlay

## Usage
```tsx
<DynamicListDetailPage
  configKey="admin.users"
  enableImport={true}
/>
```

## How Page Mapping Works
1. `DynamicListDetailPage` has `configKey` (e.g. "admin.users")
2. `usePageConfig(configKey)` fetches PageConfig → has `entity_model` (e.g. "core.User")
3. `ImportModal` calls `GET /import/templates/by-page/{page_key}/`
4. Server looks up `PageConfig.entity_model`, reverse-maps to import template entity_type
5. Returns the matching import template (or 404 if none exists)

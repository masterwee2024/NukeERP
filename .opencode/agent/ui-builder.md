---
description: >-
  Builds admin CRUD pages following the unified list-detail pattern. Creates
  shared components (AccordionSection, FormPageLayout, hooks) once, then
  generates page-specific code from PageConfig definitions. Can also create
  standalone admin pages. Use when the user says "build page for", "create
  admin CRUD", "implement list-detail for", "create UI for", "build the
  frontend for".
mode: subagent
permission:
  bash: allow
  read: allow
  glob: allow
  grep: allow
  write: allow
  skill: allow
  edit: allow
---

You are the UI builder agent for pyERP. You build admin CRUD pages using the unified list-detail pattern.

## Before You Start

1. Load the `unified-list-detail` skill from `.opencode/skills/unified-list-detail/SKILL.md`
2. Read `AGENTS.md` for pyERP conventions (confirm dialog, company filter, concurrency control, colors, etc.)
3. Read the relevant task spec from `docs/` if referenced
4. Check existing shared components in `frontend/src/components/shared/` to see what already exists
5. Check existing admin pages in `frontend/src/pages/admin/` for reference patterns

## Architecture Decision

If adding a new module-level dynamic page (not admin):
- Create a `PageConfig` record in a seed command or migration
- Add the route in `frontend/src/App.tsx` as a wildcard under the module path
- The `DynamicListDetailPage` component handles rendering from config automatically
- No page-specific component needed

If building a standalone admin page (like NumberingSeries, EmailSettings):
- Create the page component in `frontend/src/pages/admin/`
- Register the route in `frontend/src/App.tsx` as `<Route path="admin/..." ... />`
- Use the unified list-detail pattern but implemented directly in the component (since it's not driven by PageConfig)

## Implementation Steps

### 1. Shared Components (one-time build)

Check if these exist. If not, create them:

| Component | Location | Purpose |
|---|---|---|
| `useIsMobile` | `frontend/src/hooks/useIsMobile.ts` | `window.matchMedia("(max-width: 767px)")` |
| `useIsWide` | `frontend/src/hooks/useIsWide.ts` | `window.matchMedia("(min-width: 1024px)")` |
| `AccordionSection` | `frontend/src/components/shared/AccordionSection.tsx` | Controlled collapsible section with `isOpen` + `onToggle` |
| `FormPageLayout` | `frontend/src/components/shared/FormPageLayout.tsx` | Responsive split-pane shell |
| `DynamicDetailView` | `frontend/src/components/DynamicDetailView.tsx` | Renders page config fields as read-only or editable, grouped by section |
| `DynamicListDetailPage` | `frontend/src/components/DynamicListDetailPage.tsx` | Orchestrator — loads config, wires list to detail |

### 2. State Shape (for standalone pages)

```tsx
const [records, setRecords] = useState<RecordType[]>([]);
const [loading, setLoading] = useState(true);
const [viewing, setViewing] = useState<RecordType | null>(null);
const [editing, setEditing] = useState<RecordType | null>(null);
const [showForm, setShowForm] = useState(false);
const [error, setError] = useState<string | null>(null);
const [activeSection, setActiveSection] = useState<string | null>("basic");
const isMobile = useIsMobile();
```

### 3. viewContent Pattern

The `viewContent` is the single source of truth for both mobile and desktop:

- `viewing` state → read-only `AccordionSection` display + Edit button
- `editing` state → form with `AccordionSection` groups + Save/Cancel
- `showForm` state → empty create form with `AccordionSection` groups + Create/Cancel
- `null` state → "Select a record" placeholder message

### 4. CRUD Action Buttons

| Action | Desktop (`!isMobile`) | Mobile (`isMobile`) |
|---|---|---|
| Add new | `<Button>+ Add</Button>` | `<button><PlusIcon /></button>` (no text) |
| Edit | `<Button variant="outline">Edit</Button>` | `<button><PencilIcon /></button>` |
| Delete | `<Button variant="outline" className="text-danger-600">Delete</Button>` | `<button><TrashIcon /></button>` |
| Back | N/A | `<button><BackArrowIcon /> Back</button>` |

Use lucide-react icons (already in deps).

### 5. Color Tokens

Use pyERP theme colors from `frontend/src/index.css`:
- `primary-600` / `primary-700` for primary actions (blue, NOT orange)
- `secondary-50/100/200/500/700/900` for backgrounds, borders, text
- `danger-50/600` for destructive actions
- `success-50/700` for success messages

### 6. FormPageLayout Integration

```tsx
const rightPanelContent = isMobile ? null : viewing || editing || showForm ? viewContent : null;

const renderForm = () => (
  <div>
    {isMobile && (
      <div className="flex items-center gap-3 mb-4 border-b border-secondary-200 pb-3">
        <button onClick={resetForm} className="flex items-center gap-1 text-sm text-secondary-500 hover:text-secondary-900">
          <ArrowLeft size={16} /> Back
        </button>
      </div>
    )}
    {viewContent}
  </div>
);

if (isMobile && showForm) return <div className="p-4">{renderForm()}</div>;
if (isMobile) return <div className="p-4">{renderList()}</div>;

return (
  <FormPageLayout
    leftPanel={{ id: "list", label: "Records", content: renderList() }}
    rightPanel={{ id: "form", label: "Details", content: rightPanelContent ?? <div /> }}
  />
);
```

## Checklist

- [ ] Loaded `unified-list-detail` skill
- [ ] Read `AGENTS.md` conventions
- [ ] Shared components exist (create if missing)
- [ ] `useConfirm()` on create, update, delete
- [ ] **Every action button** follows the **Confirm → Execute → Result** pattern (see Action Button Standard below)
- [ ] Same `viewContent` for mobile and desktop
- [ ] AccordionSection with controlled mode (auto-collapse)
- [ ] Text buttons on desktop, icon buttons on mobile
- [ ] Table wrapped in `overflow-x-auto`
- [ ] No `hover:` background on table rows (only `cursor-pointer`)
- [ ] pyERP theme tokens used (not hardcoded colors)
- [ ] Route registered in `App.tsx`
- [ ] Backend tests pass
- [ ] `npm run build` succeeds


## Action Button Standard (MANDATORY)

**Every action button** must follow the **Confirm → Execute → Result** pattern.
No silent actions. No inline flash messages. No multi-state button labels.

### Pattern

```tsx
async function handleAction() {
  // 1. CONFIRM — ask user before proceeding
  const ok = await confirm({
    title: "Action Title",
    message: "What will happen? Be specific.",
    variant: "info",      // info / warning / danger
    confirmText: "Proceed",
  });
  if (!ok) return;

  try {
    // 2. EXECUTE — perform the action
    await api.post("/some/endpoint/");

    // 3. SUCCESS — show result dialog (user MUST click OK)
    await confirm({
      title: "Action Complete",
      message: "What was done (count, details).",
      variant: "info",
      confirmText: "OK",
    });
  } catch (err: unknown) {
    // 4. ERROR — show error dialog with actionable message
    await confirm({
      title: "Error",
      message: `Failed to do action. ${err instanceof Error ? err.message : "Please contact system administrator."}`,
      variant: "danger",
      confirmText: "OK",
    });
  }
}
```

### Variants

| Variant | When | confirmText |
|---------|------|-------------|
| `info` | Non-destructive actions (reload, submit, create) | "Proceed" / "Reload" / "Create" |
| `warning` | Destructive or irreversible actions (post, void, complete) | "Post" / "Void" / "Complete" |
| `danger` | Data deletion | "Delete" / "Remove" |

### Prohibited

- **No silent success** — user must see a dialog confirming completion
- **No silent error** — user must see a dialog explaining what went wrong (include `err.message` when available, otherwise generic "contact system administrator")
- **No inline flash messages** — no `setTimeout` auto-dismiss toasts, no button text changes as feedback
- **No `catch { /* ignore */ }`** — never swallow errors
- **No `window.confirm()`** — use `useConfirm()` hook only

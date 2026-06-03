# pyERP — Agent Instructions

> Compact reference for AI agents working in this codebase. Every line answers: "Would an agent likely miss this without help?"

---

## Quick Commands

```bash
# Backend (Python)
uv sync                           # install Python deps
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py seed_menus   # seed dynamic menu tree
uv run python manage.py seed_page_configs   # seed page configuration for all modules
uv run pytest                      # all backend tests
uv run pytest tests/backend/ap/test_supplier_invoice.py -k "test_post"  # single test
uv run ruff check .               # lint
uv run black .                    # format
uv run mypy .                     # typecheck

# Frontend (React)
cd frontend && npm install
npm run dev                       # Vite dev server (port 5173)
npm run build                     # production build
npm run test                      # Vitest
npm run test -- --run src/components/ConfirmDialog.test.tsx  # single test
npx playwright test               # E2E (requires backend running)
npx playwright test tests/e2e/specs/ap-invoice.spec.ts      # single spec

# Docker
docker compose up -d              # start all services
docker compose down
docker compose logs -f django     # backend logs
docker compose exec django python manage.py shell

# Pre-commit
uv run pre-commit run --all-files # run all hooks manually
uv run pre-commit install         # install hooks (done once)
```

## Architecture

```
pyERP/
├── apps/                    # Django apps (one per module)
│   ├── core/                # Menu, Company, User, RBAC, Audit, Notifications
│   ├── financial/           # GL, AP, AR, Bank Reconciliation, Tax/SST
│   ├── assets/              # Fixed Assets, Depreciation, Capital Allowance
│   ├── treasury/            # Cash Management, Loans, Cash Flow Forecast
│   ├── scm/                 # Items, Inventory, Warehouse, Procurement, PO, GRN
│   ├── crm/                 # Leads, Opportunities, Customers, Quotation, SO, DO
│   ├── mrp/                 # BOM, Work Centers, Routings, MRP, Work Orders, QC
│   ├── hrm/                 # Employees, Attendance, Leave, Payroll, Claims
│   └── admin_system/        # System Admin (users, roles, settings)
├── frontend/                # React + Vite + TypeScript + TailwindCSS
│   ├── src/
│   │   ├── components/      # Shared UI (ConfirmDialog, Layout, Sidebar, etc.)
│   │   ├── hooks/           # useMenu, useConfirm, useAuth, etc.
│   │   ├── pages/           # Route-level components (one per page)
│   │   └── schemas/         # Zod validation schemas
│   └── tests/
├── docs/                    # Task detail files (t001.md – t095.md)
├── tests/
│   ├── backend/             # Pytest tests (mirrors apps/ structure)
│   ├── frontend/unit/       # Vitest tests
│   └── e2e/specs/           # Playwright specs
└── docker-compose.yml
```

## Key Conventions

### Confirm Dialog (MANDATORY)
- **Every** create, update, delete, post, void, approve action uses `useConfirm()` hook
- **Never** use `window.confirm()`
- **Never** perform destructive action without confirmation
- If a CRUD action is missing confirmation, it is a bug
- Variants: `danger` (delete), `warning` (post/void), `info` (submit)

### Multi-Company Architecture
- **Master data is global** — Items, Customers, Vendors, Employees, COA have NO company_id FK
- Master data is assigned to companies via junction tables (ItemCompany, CustomerCompany, etc.)
- **Transactions are per-company** — all transaction tables have company_id FK
- **UserCompany** junction table — user can access multiple companies
- **Company Switcher** in header — switch active company, all data refetches
- **Always filter by active company**: transactions by company_id, master data by assignment
- **Never hardcode company_id** — use `request.user.current_company_id` or middleware

### Dynamic Menu System
- Menu items are **database records**, not hardcoded in React
- New menu = insert `Menu` record → appears in sidebar immediately
- Menu visibility = check user's role → `MenuRole` junction table
- Menu management: Admin → Roles & Permissions → Menu Access

### Dynamic Page Config
- All forms and lists are rendered from `PageConfig` + `PageConfigField` database tables
- Never hardcode form fields in React — use `DynamicFormPage` / `DynamicListPage` components
- To add/change a field: insert/update record in `page_config_field` table → appears on next page load
- Visual page builder at `/admin/page-builder` for managing configs
- Config includes: field type, validation, permissions, conditional display, options, formatting

### Concurrency Control (MANDATORY)
- **Every model** MUST inherit from `ConcurrencyModel` (adds created_at, updated_at, version)
- **Every API update** MUST validate `updated_at` matches last known value → 409 Conflict if mismatch
- **Every API update** MUST use `select_for_update()` for financial/inventory operations
- **Frontend** MUST handle 409 Conflict gracefully (show toast, invalidate cache, reload data)
- **Never** update a record without version check — this is a data integrity bug
- **Never** skip `select_for_update()` on financial posting or stock movements

### Performance (MANDATORY)
- **PgBouncer** in front of PostgreSQL — transaction mode, pool size 20, max client 500
- **Database indexes** on ALL ForeignKey fields, status columns, date columns, searchable text
- **Debouncing** on ALL search inputs — `useDebounce(search, 300)` — no exceptions
- **HTTP/2** enabled in Nginx for multiplexed requests
- **WebSocket** for real-time notifications only (not for general data)
- **Never** make API calls on every keystroke — always debounce search inputs
- **Never** skip database indexes on FK/status/date fields — this causes slow queries

### Portal Security (MANDATORY)
- **Internal users** CANNOT access `/portal/*` routes — enforced by middleware
- **Portal users** CANNOT access `/app/*` routes — enforced by middleware
- **Client A** CANNOT see Client B's data — API enforces customer_id scope
- **Supplier A** CANNOT see Supplier B's data — API enforces vendor_id scope
- **Internal messaging** is company-scoped — external users cannot access internal channels
- **External messaging** is entity-scoped — clients/suppliers see only their dedicated channel
- **JWT tokens** are scoped — internal (8-hour TTL) vs portal (2-hour TTL)
- **File attachments** are access-controlled — channel membership required
- **Never** return cross-entity data in portal APIs — this is a security breach
- **Never** allow portal users to access internal ERP routes — this is a security breach

### Responsive Design
- **No horizontal scroll at any viewport width** — this is non-negotiable
- Test at 375px (mobile), 768px (tablet), 1440px (desktop)
- Tables: `overflow-x-auto` in bounded container, never viewport
- Modals: `max-w-[calc(100vw-2rem)]`

### API Pattern (Django Ninja)
- All endpoints: `/api/v1/{module}/{resource}/`
- Auto-generated Swagger: `/api/docs`
- Error response: `{ "detail": "message" }` or `{ "errors": { field: [...] } }`
- Pagination: `{ "count": N, "results": [...] }`

### Database
- PostgreSQL 16 only — no SQLite (JSONB, full-text search)
- All models use `company_id` FK for multi-tenant row filtering
- UUID PK for public-facing IDs, serial for internal FKs
- Soft delete for master data (is_active flag)

### Testing
- **Pytest** for backend: models, services, API endpoints
- **Vitest** for frontend: components, hooks, utilities
- **Playwright** for E2E: full user flows
- Critical paths (GL posting, payroll calc, SST computation) require tests before merge

### Git
- **Remote**: `origin` → `https://github.com/masterwee2024/NukeERP.git`
- **Default branch**: `master` (protected — no direct pushes)
- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
- **Merge strategy**: Squash-merge PRs to `master` (never commit directly)
- **Branch naming**: `feat/description`, `fix/description`, `phase-N/description`
- **After merge**: Delete the branch immediately — stale branches cause confusion and potential overrides

## Development Workflow

### Definition of Done (DoD) — Every Task

A task is **done** when ALL of these are true:

1. **Code complete** — all deliverables in task spec are implemented
2. **Tests pass** — `uv run pytest` (backend), `npm run test` (frontend), `npx playwright test` (E2E)
3. **Coverage thresholds met** — backend ≥80%, frontend ≥70%, critical paths ≥90%
4. **Lint clean** — `uv run ruff check .` and `uv run black --check .` pass
5. **Type check clean** — `uv run mypy .` and `npx tsc --noEmit` pass
6. **Pre-commit hooks pass** — `uv run pre-commit run --all-files`
7. **No regressions** — existing tests still pass
8. **Responsive** — UI tested at 375px, 768px, 1440px (no horizontal scroll)
9. **Concurrency control** — if model has `updated_at`, API validates version
10. **Company filter** — if transaction, filters by `company_id`

### Branch Strategy

```
main                    ← production-ready, protected
├── feat/T005-menu      ← feature branches
├── feat/T010-page-config
├── fix/invoice-calc
└── phase-1/financial   ← phase branches for grouped work
```

- **Branch from**: `master` (always up-to-date)
- **Merge to**: `master` via squash-merge
- **Delete after merge**: yes
- **Never force-push to master**: protected branch

### Pull Request Process

1. **Create branch** from `main`: `git checkout -b feat/T005-menu`
2. **Commit often** — small, focused commits with conventional messages
3. **Push and create PR** — use `gh pr create` or GitHub UI
4. **PR title** = conventional commit format: `feat: implement dynamic menu system (T005)`
5. **PR description** must include:
   - What was built (link to task spec)
   - How to test it
   - Screenshots (if UI changed)
   - Checklist: tests, lint, coverage, responsive
6. **Self-review** before requesting review — read your own diff
7. **CI must pass** — all hooks, tests, lint, typecheck
8. **Squash-merge** to main — clean commit history

### Code Review Checklist

When reviewing a PR:

- [ ] **Confirm Dialog** — every destructive action uses `useConfirm()`
- [ ] **Company filter** — all queries filter by company
- [ ] **Concurrency** — `select_for_update()` on financial/inventory ops
- [ ] **No hardcoded IDs** — no `company_id=1` or `user_id=1`
- [ ] **No `window.confirm()`** — only `useConfirm()` hook
- [ ] **No horizontal scroll** — responsive design at all viewports
- [ ] **Services layer** — business logic in `services.py`, not views
- [ ] **Page Config** — forms use `DynamicFormPage`, not hardcoded fields
- [ ] **Error handling** — API errors shown to user, not swallowed
- [ ] **Tests** — new code has tests, coverage meets threshold

### Coverage Thresholds

| Layer | Tool | Minimum | Critical Paths |
|---|---|---|---|
| Backend | Pytest | ≥80% | ≥90% (GL posting, payroll, SST) |
| Frontend | Vitest | ≥70% | ≥80% (forms, hooks) |
| E2E | Playwright | — | Critical user flows only |

```bash
# Check coverage
uv run pytest --cov=apps --cov-report=term-missing
npm run test -- --coverage
```

### Hotfix Process

For production-breaking bugs:

1. **Create branch** from `main`: `git checkout -b fix/critical-invoice-calc`
2. **Fix + test** — minimal change, maximum confidence
3. **Fast-track review** — one approval required (not two)
4. **Merge to main** — squash-merge
5. **Tag release**: `git tag v1.0.1-hotfix`
6. **Deploy immediately** — no waiting for next release

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `style`, `ci`, `perf`

**Examples**:
```
feat(financial): implement GL journal entry posting
fix(hrm): correct EPF calculation for salary ≥ RM5k
chore: update Docker Compose port mappings
test(scm): add stock movement concurrency tests
docs(T005): update task spec with menu API details
```

### Agent Delegation Rules

**Sub-agents are assistants, not replacements for judgment.**

1. **Review output** — Always read sub-agent results before accepting them
2. **Verify critical items** — Never blindly trust "all checks passed" on git, financial logic, or security
3. **Investigate errors** — If a sub-agent reports failure, understand why before retrying or fixing
4. **Context matters** — Sub-agents don't see conversation history; provide clear task summaries when delegating
5. **Use as checklist** — Code review agent is pattern-based, not a replacement for human logic review
6. **Git caution** — Verify `git status` and `git diff` before pushing; fix malformed commits immediately
7. **Escalate doubts** — If uncertain about a sub-agent's result, run the check manually or ask the user

### Task Workflow

**MANDATORY: Before starting any task, acknowledge these steps:**

- [ ] 1. **Read task spec** — `docs/tXXX.md` has everything
- [ ] 2. **Check dependencies** — task spec lists what must be done first
- [ ] 3. **Create branch** — DELEGATE to git agent: "create branch for TXXX"
- [ ] 4. **Implement** — follow architecture conventions in this file
- [ ] 5. **Write tests** — match coverage thresholds
- [ ] 6. **Run checks** — DELEGATE to test-runner agent: "run tests"
- [ ] 7. **Self-review** — DELEGATE to code-review agent: "review my changes"
- [ ] 8. **Update task spec** — mark deliverables as done, fill test results table
- [ ] 9. **Create PR** — DELEGATE to git agent: "create PR for TXXX"
- [ ] 10. **Merge** — squash-merge after CI passes

**If you skip step 3 or 6, you are violating project rules.**

### Test Runner Agent

All test execution is delegated to the **test-runner agent** (`.opencode/agent/test-runner.md`).

**Trigger phrases:** "run tests", "test everything", "check all", "verify"

**When to use:**
- After implementing a task — verify no regressions
- Before creating a PR — ensure all checks pass
- After fixing a bug — confirm the fix works
- When switching tasks — clean slate check

**What it runs:**
| Step | Check | Command |
|---|---|---|
| 1 | Python lint | `uv run ruff check .` |
| 2 | Python format | `uv run black --check .` |
| 3 | Backend tests | `uv run pytest tests/backend/ -v` |
| 4 | Frontend lint | `npm run lint` |
| 5 | Frontend format | `npm run format:check` |
| 6 | TypeScript | `npx tsc --noEmit` |
| 7 | Frontend tests | `npm run test:run` |
| 8 | Build | `npm run build` |
| 9 | Django check | `uv run python manage.py check` |

**Do NOT run tests manually** — always use the agent. It runs faster, reports consistently, and catches issues across all layers.

### Git/PR Agent

All git operations are delegated to the **git agent** (`.opencode/agent/git-pr.md`).

**Trigger phrases:** "create branch", "commit", "create PR", "push changes", "finish task"

**When to use:**
- Starting a new task — create branch
- After implementing — commit with conventional format
- Before review — push and create PR

**What it does:**
| Step | Action | Command |
|---|---|---|
| 1 | Create branch | `git checkout -b feat/TXXX-description` |
| 2 | Verify status | `git status && git diff --stat` |
| 3 | Stage & commit | `git add -A && git commit -m "..."` |
| 4 | Push | `git push -u origin <branch>` |
| 5 | Create PR | `gh pr create --title "..." --body "..."` |

**Commit format:** `<type>(<scope>): <description>` with bullet point body

**CRITICAL**: After PR merge, always delete the branch: `git branch -D <branch>` — stale branches cause accidental overrides.

### Code Review Agent

All code reviews are delegated to the **review agent** (`.opencode/agent/code-review.md`).

**Trigger phrases:** "review code", "check my changes", "self-review", "review PR"

**When to use:**
- Before creating a PR — catch convention violations
- After implementing — verify all conventions followed
- When reviewing someone else's PR

**What it checks:**
| Priority | Check | Violation |
|---|---|---|
| CRITICAL | Confirm Dialog | `window.confirm()` usage |
| CRITICAL | Company Filter | Missing `company_id` filter |
| CRITICAL | Concurrency | Missing `select_for_update()` |
| HIGH | Hardcoded IDs | `company_id=1`, `user_id=1` |
| MEDIUM | Services Layer | Business logic in views |
| LOW | Responsive | Missing `overflow-x-auto` |

**Do NOT review code manually** — always use the agent for consistent coverage.

## Malaysian Compliance Gotchas

- **SST**: Sales tax (5-10%), Service tax (6%) — not GST. SST-02 return.
- **EPF**: Employee 11%, Employer 12% (salary < RM5k) or 13% (≥ RM5k)
- **SOCSO**: Wage-bracket based, not percentage. Two categories.
- **EIS**: 0.2% each employer + employee, capped at ceiling
- **PCB**: Monthly Tax Deduction — use LHDN MTD schedule, not simple percentage
- **e-Invoicing**: LHDN MyInvois API — mandatory phased rollout from Aug 2024
- **Capital Allowance**: Schedule 3 ITA 1967 — separate from book depreciation

## Graphify

This project uses Graphify for knowledge graph generation. Before scanning the codebase:

1. Read the Graphify skill at `~/.claude/skills/graphify/SKILL.md` or `~/.config/opencode/skills/graphify/SKILL.md`
2. Run Graphify to generate the knowledge graph JSON + HTML
3. The graph provides module-level community detection for faster code navigation

## Common Pitfalls

1. **Forgetting `company_id` filter** — every list query must filter by `request.user.company_id`
2. **Using `window.confirm()`** — use `useConfirm()` hook instead
3. **Hardcoding menu items** — menus come from database via `useMenu()` hook
4. **Horizontal scroll** — test every page at 375px width
5. **Posting to closed period** — always check `Period.is_open` before posting
6. **Missing GL entries** — every financial transaction must create balanced debits/credits
7. **Not using services layer** — business logic goes in `services.py`, never in views/serializers
8. **Hardcoding form fields** — use Page Config system (T010-T012) instead
9. **Ignoring field_config** — every form field must come from PageConfigField, not React code
10. **Adding company_id to master data** — master data is global; use junction tables for assignment
11. **Forgetting company filter** — master data queries must filter by company assignment, not company_id
12. **API auth uses JWTAuth only** — `SessionAuth` was removed from the auth stack. All API calls must provide `Authorization: Bearer <token>`. Tests must use JWT tokens (via `AccessToken.for_user(user)`), not `force_login()`. CSRF is handled by Django's standard `CsrfViewMiddleware` — API routes are considered safe because they don't use session cookies.

## Industry Modules (Extensible Platform)

pyERP is a **modular ERP platform**. Core modules (Finance, Assets, Facility, HRM, SCM, CRM, MRP) are always installed. Industry-specific modules are pluggable Django apps that extend the core.

### How It Works

1. **Core modules** provide reusable APIs (GL posting, asset management, employee management, etc.)
2. **Industry modules** implement domain-specific logic and register with the platform
3. **Industry templates** (JSON configs) pre-configure menus, workflows, GL accounts for a specific industry

### Adding a New Industry Module

To create a new industry module (e.g., Hotel, Retail, Plantation):

1. Create Django app: `apps/{industry_name}/`
2. Register with platform in `__init__.py`:
   ```python
   from apps.core.platform.module_registry import registry

   MODULE_CONFIG = {
       "name": "Hotel Management",
       "code": "hotel",
       "dependencies": ["finance", "hrm", "facility_management"],
       "menu_items": [...],
       "page_configs": [...],
       "workflows": [...],
       "gl_accounts": [...],
       "signals_emitted": ["room.booked", "guest.checked_in"],
       "signals_handled": ["invoice.posted", "payment.received"],
   }
   registry.register_module(MODULE_CONFIG)
   ```
3. Use core module APIs for common operations:
   - Finance: `finance.api.create_journal_entry()`, `finance.api.create_invoice()`
   - Assets: `assets.api.register_asset()`, `assets.api.create_work_order()`
   - HRM: `hrm.api.manage_employee()`, `hrm.api.run_payroll()`
   - SCM: `scm.api.create_stock_movement()`, `scm.api.create_purchase_order()`
4. Create industry-specific models, services, APIs
5. Add menu items via dynamic menu (T005)
6. Add page configs via page config system (T010)
7. Add workflows via approval workflow system (T016)
8. Add GL accounts via GL account mapping (T029c)

### Signal/Event System

Core modules emit events that industry modules can subscribe to:
- `invoice.posted` — Finance
- `payment.received` — Finance
- `asset.registered` — Asset Management
- `employee.hired` — HRM
- `stock.received` — SCM
- `facility.utility.reading` — Facility Management

### Reference Implementation

Property Management (T200-T208) is the first reference industry module.
Task details: `docs/t200.md` through `docs/t208.md`

### Industry Module Structure

```
apps/{industry_name}/
├── __init__.py          # MODULE_CONFIG registration
├── models.py            # Industry-specific models
├── services.py          # Business logic
├── api/                 # Industry-specific endpoints
├── signals.py           # Event handlers
├── management/commands/  # Seed data
└── tests/
```

### Key Rules for Industry Modules

- **Never modify core module code** — extend via APIs and signals
- **Use core GL posting** — don't create separate GL systems
- **Use core approval workflows** — don't build separate approval logic
- **Use core RBAC** — don't create separate permission systems
- **Use Page Config** — don't hardcode forms in React
- **Use Dynamic Menu** — don't hardcode menu items
- **Follow ConcurrencyModel** — all models must inherit from it
- **Follow company scoping** — transactions per company, master data global

# pyERP — Agent Instructions

> Compact reference for AI agents working in this codebase. Every line answers: "Would an agent likely miss this without help?"

---

## Quick Commands

```bash
# Backend (Python)
poetry install                    # install Python deps
poetry run python manage.py migrate
poetry run python manage.py runserver
poetry run python manage.py seed_menus   # seed dynamic menu tree
poetry run python manage.py seed_page_configs   # seed page configuration for all modules
poetry run pytest                  # all backend tests
poetry run pytest tests/backend/ap/test_supplier_invoice.py -k "test_post"  # single test
poetry run ruff check .           # lint
poetry run black .                # format
poetry run mypy .                 # typecheck

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
│   └── admin/               # System Admin (users, roles, settings)
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
- Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`
- Squash-merge to `main`
- Branch naming: `feat/description`, `fix/description`, `phase-N/description`

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

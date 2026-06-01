# pyERP — Task Lists

> Master index of all tasks. Each task links to its detail file in `docs/`.

---

## Legend

- **Phase**: Build phase (0–8)
- **Depends On**: Tasks that must complete before this one starts
- **Tests**: B = Pytest (backend), F = Vitest (frontend), E = Playwright (E2E)

---

## Phase 0 — Scaffolding & Foundation

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T001 | Project Initialization | Django project + React+Vite+TS+TailwindCSS scaffolded under `frontend/`. Poetry/uv for Python deps, npm for frontend. | — | — | [docs/t001.md](docs/t001.md) |
| T002 | Docker Compose Dev Environment | `docker-compose.yml` with PostgreSQL 16, Redis, Django app, React dev server, MinIO. Hot-reload both sides. | T001 | — | [docs/t002.md](docs/t002.md) |
| T003 | Git Repository & Graphify Setup | `git init`, `.gitignore`, `.gitattributes`. Graphify index — generate knowledge graph JSON + HTML. Pre-commit hooks. | T001 | — | [docs/t003.md](docs/t003.md) |
| T004 | CI/CD Pipeline | GitHub Actions: Ruff lint, Black format, mypy typecheck, pytest, Vitest, Playwright. PR gating on all passing. | T002, T003 | — | [docs/t004.md](docs/t004.md) |
| T005 | Dynamic Menu System | Menu model with self-referencing parent FK. MenuRole junction table. Seed data with full menu tree. API returns filtered tree by user role. | T001 | B, F, E | [docs/t005.md](docs/t005.md) |
| T006 | Responsive Layout Shell | Sidebar + header + content area. Mobile hamburger, desktop persistent sidebar. `overflow-x: hidden` global. Company Switcher in header. CSS variable theme tokens. | T001, T005 | F, E | [docs/t006.md](docs/t006.md) |
| T007 | Confirm Dialog & Core UI Components | Reusable `ConfirmDialog` component. `useConfirm()` hook for any CRUD action. `useApproval()` hook for submit/approve/reject/delegate. Variants: danger/warning/info. Focus trap, keyboard accessible. Every create/update/delete/post/void/approve uses this — no `window.confirm()`. | T001 | F, E | [docs/t007.md](docs/t007.md) |
| T008 | Authentication System | Custom `User` model (email login). JWT auth via simplejwt. Login/register/forgot-password/reset-password pages. Token refresh. | T006 | B, F, E | [docs/t008.md](docs/t008.md) |
| T009 | API Layer Foundation | Django Ninja configured with `/api/docs` Swagger. Base CRUD pattern, error response schema, pagination, sorting, filtering utilities. API versioning (`/api/v1/`). Concurrency control (TimestampedModel, ConcurrencyModel, 409 handling). | T001 | B | [docs/t009.md](docs/t009.md) |
| T009a | Document Attachments | Global attachment service — any record can have file attachments. Upload, download, preview, delete. Used by invoices, employees, items, etc. | T009 | B | [docs/t009a.md](docs/t009a.md) |
| T009b | Module Plugin Interface | Module registration system, signal bus for inter-module communication, extension point documentation, module dependency management. | T009 | B | [docs/t009b.md](docs/t009b.md) |
| T009c | Industry Template Engine | Load/install industry templates from JSON. Configure modules, menus, workflows, GL accounts for specific industry. | T009b | B | [docs/t009c.md](docs/t009c.md) |
| T009d | Data Migration Framework | CSV import engine, column mapping, validation, import history, rollback, downloadable templates for all entities. | T009 | B, E | [docs/t009d.md](docs/t009d.md) |
| T009e | Opening Balance Migration | Migration wizard for GL, AP, AR, inventory, asset opening balances. Step-by-step with validation. Creates opening entries. | T009d | B, E | [docs/t009e.md](docs/t009e.md) |
| T009f | Transaction Migration | Import pending (open POs, SOs) and historical transactions. Fresh start vs full migration option. | T009d, T009e | B, E | [docs/t009f.md](docs/t009f.md) |

---

## Phase 1 — Core Platform

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T010 | Page Config Engine | Database-driven page configuration system. `PageConfig` + `PageConfigField` models with responsive view config. CRUD API. Seed data for all modules. | T009 | B, E | [docs/t010.md](docs/t010.md) |
| T011 | Dynamic Page Renderer | Generic React components: DynamicFormPage, DynamicListPage, DynamicDetailPage, DynamicDashboardPage. Responsive rendering (table→card on mobile). 20+ field types. Validation. Conditional display. Company-aware filtering. | T010 | F, E | [docs/t011.md](docs/t011.md) |
| T012 | Visual Page Builder UI | Drag-and-drop admin page builder. Component palette, live canvas, property editor with responsive tab. JSON export/import. Clone page config. | T011 | F, E | [docs/t012.md](docs/t012.md) |
| T013 | Company & Multi-Company Architecture | `Company` with group hierarchy (parent FK, is_group). `UserCompany` junction. Company Switcher. Master data is global (no company_id FK). Transactions per-company. Company middleware. | T009 | B, E | [docs/t013.md](docs/t013.md) |
| T014 | Role-Based Access Control (RBAC) | Custom permission model: `Role` → `Permission` (module, action). Assign roles to users. `@permission_required` decorator. UI route guards. Link MenuRole from T005. | T005, T008 | B, F, E | [docs/t014.md](docs/t014.md) |
| T015 | User Management UI | User CRUD, role assignment, company assignment (via UserCompany), activate/deactivate, password reset by admin, login history. | T014 | F, E | [docs/t015.md](docs/t015.md) |
| T016 | Approval Workflow Engine | Visual workflow engine with conditional routing, multi-level sequential/parallel approval, company-scoped, creator≠approver. `useApproval()` hook integration. Reusable across all modules. | T009, T013 | B, E | [docs/t016.md](docs/t016.md) |
| T016a | Visual Workflow Designer | Drag-and-drop workflow designer (react-flow). Nodes: Start, End, Approve, Condition, Notify, Action. Properties panel. Save/load. Company-scoped templates. | T016 | F, E | [docs/t016a.md](docs/t016a.md) |
| T016b | Org Chart | Visual org chart (d3-hierarchy). Drag-and-drop restructuring. Approval chain helper. Integration with workflow designer. Company-scoped. | T076, T016 | B, F, E | [docs/t016b.md](docs/t016b.md) |
| T016c | Centralized Approval Page + Mobile Notifications | Single page for all pending approvals. Full document context. Quick approve/reject. Batch approve. PWA push notifications. Email approve/reject links (process from email without login). | T016, T019 | B, F, E | [docs/t016c.md](docs/t016c.md) |
| T016d | Approval Workflow Policy | Condition-based auto-routing. Policies evaluate document data to select workflow. Priority ordering. Company-scoped. Test mode. | T016 | B, E | [docs/t016d.md](docs/t016d.md) |
| T017 | Numbering Series Engine | Configurable document numbering: prefix + date component + running number. Per-document-type, per-year reset. Concurrency-safe (DB lock). | T009 | B | [docs/t017.md](docs/t017.md) |
| T018 | Audit Log System | Immutable audit trail: model name, record ID, action, changed fields (JSON diff), user, timestamp, IP. | T009 | B | [docs/t018.md](docs/t018.md) |
| T018a | Advanced Audit Trail | Bulk ops, login/logout, export tracking, config changes, file audit, approval linkage, retention policy, export, dashboard. | T018, T009a, T016, T009d | B, F | [docs/t018a.md](docs/t018a.md) |
| T019 | Notification Framework | In-app notification bell + email + PWA push. Email approve/reject links (process without login). Push subscription management. Notification types configurable. Celery tasks for async dispatch. | T009 | B, F, E | [docs/t019.md](docs/t019.md) |
| T019a | Internal Messaging: Engine | Channels, DMs, threads, file attachments, link previews, system messages, search, read/unread, WebSocket delivery. | T019, T008, T013 | B | [docs/t019a.md](docs/t019a.md) |
| T019b | Internal Messaging: UI | Chat interface, channel list, message list, thread panel, file upload, @mentions, emoji, search, mobile-responsive. | T019a | F, E | [docs/t019b.md](docs/t019b.md) |
| T020 | Django Admin Customization | Custom admin site with company filtering, role-restricted views. Inline models. Custom admin actions. | T014 | B | [docs/t020.md](docs/t020.md) |

---

## Phase 2 — Financial Foundation

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T021 | Chart of Accounts | Hierarchical `Account` model — global (no company_id FK). `AccountCompany` junction for per-company assignment. MFRS category mapping. Import from template. | T013 | B, E | [docs/t021.md](docs/t021.md) |
| T022 | Journal Entry CRUD | Create JE with multiple debit/credit lines. Auto-balancing validation. Edit unposted entries. Delete with reversal. Reference document linking. | T017, T021 | B, F, E | [docs/t022.md](docs/t022.md) |
| T022a | Recurring Journals | Recurring journal templates for monthly prepayments, accruals. Schedule generation via Celery. Preview before generate. | T022, T024 | B | [docs/t022a.md](docs/t022a.md) |
| T023 | Journal Entry Approval & Posting | Multi-level approval via T016 workflow. Posting creates immutable GL entries. Posted entries cannot be edited — only reversed. Period validation. | T016, T022 | B, E | [docs/t023.md](docs/t023.md) |
| T024 | Period Management | Close/reopen fiscal periods. Prevent posting to closed periods. Year-end close: transfer P&L to retained earnings. | T013, T023 | B, E | [docs/t024.md](docs/t024.md) |
| T025 | Trial Balance Report | GL aggregation by account. Period range filter. Drill-down to account detail. Export to PDF/Excel. | T021, T023 | B, F | [docs/t025.md](docs/t025.md) |
| T026 | Profit & Loss Statement | Configurable P&L template. Multi-period comparison. Departmental P&L. Export. | T025 | B, F, E | [docs/t026.md](docs/t026.md) |
| T027 | Balance Sheet | Configurable BS template. Comparative periods. Export. Asset = Liability + Equity validation. | T025 | B, F | [docs/t027.md](docs/t027.md) |
| T028 | Cash Flow Statement | Direct & indirect method. Cash movement from operations/investing/financing. Auto-generated from cash/bank GL entries. | T025 | B, F | [docs/t028.md](docs/t028.md) |
| T028a | Budgeting | Departmental budgets per period. Budget vs actual comparison. Variance analysis. Budget alerts. Approval workflow. | T021, T024 | B, F, E | [docs/t028a.md](docs/t028a.md) |
| T028b | WIP Accounting | Work-in-Progress cost tracking. Material/labour/overhead in WIP. Transfer to finished goods. WIP valuation. | T072, T021 | B | [docs/t028b.md](docs/t028b.md) |
| T028c | Standard Costing | Standard cost per item. Roll-up from BOM + routing. Revision control. Actual vs standard comparison. | T028b, T075 | B | [docs/t028c.md](docs/t028c.md) |
| T028d | Variance Analysis | Six variances: material price/usage, labour rate/efficiency, overhead spending/volume. GL posting. Trend analysis. | T028c | B, F | [docs/t028d.md](docs/t028d.md) |
| T028e | Cost Centre Accounting | Cost centres by department/work center. Cost allocation. Departmental P&L. Budget by cost centre. | T021 | B, F | [docs/t028e.md](docs/t028e.md) |
| T029 | Tax Codes & SST Engine | `TaxCode` model — global. `TaxRate` with effective dates. Tax calculation on invoice lines. SST-02 output data. | T013 | B, E | [docs/t029.md](docs/t029.md) |
| T029a | Withholding Tax | WHT deduction on payments to contractors, non-residents. WHT rates per LHDN. Auto-calculate, GL entries, certificate, remittance. | T029, T030 | B, E | [docs/t029a.md](docs/t029a.md) |
| T029b | Configurable Aging Buckets | Company-configurable aging periods (not hardcoded 30/60/90/120). AR and AP aging reports use custom buckets. | T029 | B | [docs/t029b.md](docs/t029b.md) |
| T029c | GL Account Mapping | Configurable account mapping per company (AP control, AR control, revenue, expense, forex, WHT, payroll payable). No hardcoded accounts. | T021 | B | [docs/t029c.md](docs/t029c.md) |
| T030 | Accounts Payable — Supplier Invoice | `SupplierInvoice` CRUD — per-company. Vendor filtered by VendorCompany assignment. Line items with tax code, GL account. 3-way match. Aging. | T016, T017, T021, T029, T045 | B, F, E | [docs/t030.md](docs/t030.md) |
| T031 | Accounts Payable — Payment Runs | Payment proposal. Payment method. Generate payment file. Allocate payments to invoices. Supplier statement. | T030 | B, E | [docs/t031.md](docs/t031.md) |
| T032 | Accounts Receivable — Customer Invoice | `CustomerInvoice` CRUD — per-company. Customer filtered by CustomerCompany assignment. Line items with tax. SST validation. Aging. | T016, T017, T021, T029, T045 | B, F, E | [docs/t032.md](docs/t032.md) |
| T033 | Accounts Receivable — Credit Notes & Collections | Credit note creation. Debit note. Dunning letter generation. Bad debt provision. Payment allocation. | T032 | B, E | [docs/t033.md](docs/t033.md) |
| T034 | Bank Reconciliation | Upload bank statement (CSV/OFX). Auto-match rules. Manual match/unmatch. Reconciliation report. | T030, T031, T032, T033 | B, F, E | [docs/t034.md](docs/t034.md) |
| T034a | Exchange Rate Management | `ExchangeRate` model — source/target currency, rate, date, type. CRUD. Rate history. Bulk import. | T013, T021 | B, E | [docs/t034a.md](docs/t034a.md) |
| T034b | Forex Gain/Loss Revaluation | Realised forex on payment. Unrealised forex on period-end revaluation. Semi-automatic revaluation. GL entries. Forex GL accounts. | T034a, T030, T031, T032, T033 | B, E | [docs/t034b.md](docs/t034b.md) |

---

## Phase 3 — Fixed Assets, Treasury & Inter-Company

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T035 | Inter-Company Transaction Engine | Automated inter-company posting when group companies transact. Elimination entries. Consolidation report (group P&L, BS). | T013, T021, T030, T032 | B, E | [docs/t035.md](docs/t035.md) |
| T036 | Fixed Asset Register | `FixedAsset` model — per-company. Asset categories. Barcode/label print. | T013 | B, E | [docs/t036.md](docs/t036.md) |
| T036a | Asset Revaluation | Revalue asset to fair value. Revaluation surplus/deficit. Depreciation adjustment. MFRS 116 compliant. | T036 | B, E | [docs/t036a.md](docs/t036a.md) |
| T036b | Asset Insurance | Insurance policy tracking, asset linking, claims, expiry alerts. | T036 | B, E | [docs/t036b.md](docs/t036b.md) |
| T036c | Preventive Maintenance | Maintenance schedules (time/usage-based), auto-generate WOs, calendar, checklist. Internal team or vendor. | T036, T016 | B, E | [docs/t036c.md](docs/t036c.md) |
| T036d | Corrective Maintenance & Work Orders | Breakdown repair, WO lifecycle, downtime tracking, root cause, cost tracking, spare parts. | T036c | B, E | [docs/t036d.md](docs/t036d.md) |
| T036e | Facility Management | Facility register (building→floor→room→zone), utility metering, cost allocation, building maintenance, compliance. | T036, T028e | B, E | [docs/t036e.md](docs/t036e.md) |
| T036f | Maintenance Contracts & Vendor | Contract management, SLA tracking, vendor performance, renewal alerts, internal vs outsourced comparison. | T036d | B, E | [docs/t036f.md](docs/t036f.md) |
| T036g | Equipment Allocation & Usage | Equipment to projects, usage logging, cost per hour, rental vs owned, transfer. Feeds into T101. | T036, T100 | B, E | [docs/t036g.md](docs/t036g.md) |
| T037 | Depreciation Engine | SLM: cost / useful life. RBM: net book value × rate%. Depreciation per period. GL integration. | T036 | B | [docs/t037.md](docs/t037.md) |
| T038 | Asset Disposal & Transfer | Disposal: sale, scrap, donation. Calculate gain/loss. Transfer between locations/departments. Approval workflow. | T036, T037 | B, E | [docs/t038.md](docs/t038.md) |
| T039 | Capital Allowance Schedules | Schedule 3 ITA 1967: IA + AA. Category-based rates. Notional allowance on disposal. CA report. | T036 | B | [docs/t039.md](docs/t039.md) |
| T040 | Cash Management | Cash accounts ledger. Cash position dashboard. Cash transfer between accounts. | T021 | B, E | [docs/t040.md](docs/t040.md) |
| T041 | Bank Account Management | `BankAccount` model — per-company. Bank balance vs GL reconciliation. | T021 | B, E | [docs/t041.md](docs/t041.md) |
| T041a | Bank Feed Integration | Auto bank statement import (CSV, OFX, MT940, CAMT.053). Scheduled import via Celery. Auto-match rules. | T041 | B, E | [docs/t041a.md](docs/t041a.md) |
| T041b | Bank Guarantee / Fixed Deposit | BG tracking (amount, purpose, expiry). FD tracking with interest accrual. Renewal alerts. | T041 | B, E | [docs/t041b.md](docs/t041b.md) |
| T041c | Investment Tracking | Portfolio tracking (FD, unit trusts, shares). Valuation, income recording, unrealised gain/loss. | T041 | B, E | [docs/t041c.md](docs/t041c.md) |
| T041d | Multi-Currency Bank Accounts | Foreign currency bank balances. Inter-currency transfers with forex. Bank balance revaluation. | T041, T034a | B, E | [docs/t041d.md](docs/t041d.md) |
| T042 | Petty Cash | Petty cash fund. Reimbursement requests. Top-up. Cash count reconciliation. | T040 | B, E | [docs/t042.md](docs/t042.md) |
| T043 | Cash Flow Forecasting | Projected inflows/outflows. Weekly/monthly view. Scenario analysis. | T040, T041 | B, F | [docs/t043.md](docs/t043.md) |
| T044 | Loan Management | Loan master. Amortization schedule. Interest accrual JE. Repayment tracking. | T021 | B, E | [docs/t044.md](docs/t044.md) |

---

## Phase 4 — Supply Chain Management

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T045 | Item Master | `Item` model — global (no company_id FK). `ItemCompany` junction with per-company price overrides. | T013 | B, E | [docs/t045.md](docs/t045.md) |
| T046 | Unit of Measure (UoM) | Two-layer UoM: `UoMCategory` + `UoM` (global standard + user-definable) + `ItemPackaging`. Conversion formula. Seed standard units. | T045 | B, E | [docs/t046.md](docs/t046.md) |
| T047 | Multi-Warehouse Setup | `Warehouse` model — per-company (company_id FK). Stock report by warehouse. | T013 | B, E | [docs/t047.md](docs/t047.md) |
| T048 | Bin Location Management | `BinLocation` within warehouse. Item-bin assignment. Pick path optimization. | T047 | B, E | [docs/t048.md](docs/t048.md) |
| T049 | Stock Movements & Ledger | GRN (in), delivery (out), transfer, adjustment, return. `StockLedger`. FIFO/Weighted Avg cost. Negative stock prevention. | T045, T047 | B | [docs/t049.md](docs/t049.md) |
| T050 | Stock Valuation Report | Inventory valuation. FIFO layers. Weighted avg cost. Period-end stock value. Aging report. | T049 | B, F | [docs/t050.md](docs/t050.md) |
| T049a | Landed Cost Adjustments | Freight, insurance, customs duty allocation to inventory cost. Three methods: by value, quantity, weight. GL entries. | T049, T054 | B, E | [docs/t049a.md](docs/t049a.md) |
| T049b | Cost Adjustments | Manual unit cost correction. Stock ledger update. GL entries. Adjustment history. | T049 | B | [docs/t049b.md](docs/t049b.md) |
| T049c | Stock Issue (Non-Trading) | Issue inventory for internal use (maintenance, packaging, consumables). GL debits expense, not COGS. | T049 | B, E | [docs/t049c.md](docs/t049c.md) |
| T049d | Stock Receipts (Non-Purchase) | Receipt types: return from customer, production output, opening stock, donation, sample, inter-company. Different GL per type. | T049 | B, E | [docs/t049d.md](docs/t049d.md) |
| T051 | Purchase Requisition | `PurchaseRequisition` CRUD — per-company. Vendor filtered by VendorCompany. Approval workflow. Convert to RFQ/PO. | T016, T045 | B, F, E | [docs/t051.md](docs/t051.md) |
| T052 | Request for Quotation (RFQ) | Create RFQ from PR. Send to multiple vendors. Vendor response. Comparison matrix. Select winner → PO. | T051 | B, E | [docs/t052.md](docs/t052.md) |
| T053 | Purchase Order | `PurchaseOrder` CRUD — per-company. Copy from PR/RFQ. Tax calculation. Approval. Print/email. | T016, T017, T045, T046, T052 | B, F, E | [docs/t053.md](docs/t053.md) |
| T054 | Goods Receiving (GRN) | `GoodsReceiptNote` against PO. Partial receipt. QC hold. Lot/serial capture. Auto stock movement. | T049, T053 | B, E | [docs/t054.md](docs/t054.md) |
| T055 | Stock Take & Cycle Count | Stock take sheet generation. Count entry. Variance report. Adjustment approval. ABC analysis. | T049 | B, E | [docs/t055.md](docs/t055.md) |
| T056 | Vendor Management | `Vendor` — global. `VendorCompany` junction with per-company overrides. Performance scoring. | T045 | B, E | [docs/t056.md](docs/t056.md) |

---

## Phase 5 — Customer Relationship Management

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T057 | Lead Management | `Lead` model — per-company. Lead assignment. Activity log. Convert to Customer + Opportunity. | T009 | B, F, E | [docs/t057.md](docs/t057.md) |
| T058 | Opportunity Pipeline | Kanban stages. Expected value, probability %, expected close date. Win/loss reasons. Sales forecast. | T057 | B, F, E | [docs/t058.md](docs/t058.md) |
| T059 | Customer Master | `Customer` — global. `CustomerCompany` junction with per-company credit limit overrides. 360° view. | T013, T029 | B, F, E | [docs/t059.md](docs/t059.md) |
| T060 | Sales Quotation | `SalesQuotation` CRUD — per-company. Customer filtered by CustomerCompany. Discount, tax, validity. Convert to SO. PDF. | T017, T045, T059 | B, F, E | [docs/t060.md](docs/t060.md) |
| T061 | Sales Order Management | `SalesOrder` CRUD — per-company. Copy from quotation. Backorder. Credit limit check. | T060 | B, F, E | [docs/t061.md](docs/t061.md) |
| T062 | Delivery Order | `DeliveryOrder` from Sales Order. Pick list. Partial delivery. Serial/batch. DO print. | T049, T061 | B, E | [docs/t062.md](docs/t062.md) |
| T063 | Customer Invoicing | Invoice from Delivery Order. Invoice numbering. Tax. GL posting (AR debit, Revenue credit, Tax credit). | T017, T029, T062 | B, E | [docs/t063.md](docs/t063.md) |
| T064 | After-Sales / RMA | RMA creation. Receipt → inspection → credit/repair/replace. Service tickets. Warranty validation. | T059 | B, E | [docs/t064.md](docs/t064.md) |
| T065 | Customer Portal (Basic) | Customer login. View own quotations, orders, invoices, statements. Download PDFs. Submit support ticket. | T059, T060, T061, T063 | F, E | [docs/t065.md](docs/t065.md) |
| T065a | Client Portal (Full) | Full client portal: documents, payments, support tickets, delivery tracking, messaging, account balance, PWA. | T065c, T032, T063, T062, T019a | B, F, E | [docs/t065a.md](docs/t065a.md) |
| T065b | Supplier Portal | Supplier portal: PO view, invoice submission, RFQ response, delivery updates, payment status, messaging. | T065c, T053, T052, T019a | B, F, E | [docs/t065b.md](docs/t065b.md) |
| T065c | Portal Shared Components & Security | Portal layout, auth, navigation, notifications, responsive design, internal/external security boundary, data isolation. | T008, T013 | B, F, E | [docs/t065c.md](docs/t065c.md) |
| T062a | Logistics (Picking, Sorting, QR) | Pick list generation, sorting, loading plan, delivery confirmation with QR code scanning, GPS, proof of delivery. Mobile-optimized. | T062 | B, E | [docs/t062a.md](docs/t062a.md) |
| T063a | Sales Returns | Return authorisation workflow, inspect, credit note, stock adjustment, write-off, return reason tracking. | T063, T049 | B, E | [docs/t063a.md](docs/t063a.md) |
| T063b | Consignment Sales | Goods sent to customer (ownership retained), settlement on sell-through, return of unsold. Consignment stock report. | T063, T062 | B, E | [docs/t063b.md](docs/t063b.md) |
| T063c | Product Warranty | Warranty tracking by serial number, warranty claims, expiry alerts, warranty cost provision. | T063 | B, E | [docs/t063c.md](docs/t063c.md) |

---

## Phase 6 — Manufacturing Resource Planning

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T066 | Bill of Materials (BOM) | `BOM` model — global. Multi-level tree view. Where-used report. | T045, T046 | B, F, E | [docs/t066.md](docs/t066.md) |
| T067 | BOM Revisions & Versioning | Revision control. Effective date range. Approval workflow. Compare revisions diff. | T066 | B, E | [docs/t067.md](docs/t067.md) |
| T068 | Work Centers | `WorkCenter` model — per-company. Capacity, efficiency %, cost/hour. Capacity load chart. | T013 | B, E | [docs/t068.md](docs/t068.md) |
| T069 | Routings & Operations | `Routing` linked to BOM. Operation sequence. Multiple routings per item. | T066, T068 | B, E | [docs/t069.md](docs/t069.md) |
| T070 | Master Production Schedule (MPS) | MPS grid: item × time bucket. Demand forecast. Rough-cut capacity check. | T045, T068 | B, F | [docs/t070.md](docs/t070.md) |
| T071 | MRP Run Engine | Netting calculation. Lead time offset. Planned orders. Action messages. Pegging. | T049, T070 | B | [docs/t071.md](docs/t071.md) |
| T072 | Work Orders | `WorkOrder` CRUD — per-company. Material issue. Labour booking. Completion → finished goods receipt. Cost accumulation. | T066, T069, T071 | B, E | [docs/t072.md](docs/t072.md) |
| T073 | Shop Floor Execution | Work center queue. Operation start/stop clocking. Scrap/rework recording. Production output. | T068, T072 | B, E | [docs/t073.md](docs/t073.md) |
| T074 | Quality Control Plans | QC plan per item/routing. QC results. Non-conformance tracking. Certificate of Analysis. | T069 | B, E | [docs/t074.md](docs/t074.md) |
| T075 | Product Costing | Standard cost roll-up. Actual cost via WO. Variance analysis. Cost update. | T066, T069, T072 | B | [docs/t075.md](docs/t075.md) |
| T075a | Overhead Absorption | Predetermined overhead rates, five absorption methods, over/under absorption analysis, GL entries. | T068, T028e | B | [docs/t075a.md](docs/t075a.md) |
| T075b | Direct/Indirect Cost Classification | Cost classification system, direct vs indirect breakdown, cost structure per item. | T075a | B, F | [docs/t075b.md](docs/t075b.md) |
| T075c | Marginal Costing | Contribution margin, break-even analysis, CVP, absorption vs marginal comparison. | T075b | B, F | [docs/t075c.md](docs/t075c.md) |

---

## Phase 7 — Human Resource Management

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T076 | Employee Master | `Employee` — global. `EmployeeCompany` junction with department and is_primary. Bank details. Document vault. | T013 | B, E | [docs/t076.md](docs/t076.md) |
| T077 | Organization Structure | `Department`, `Designation`, `Grade`. Reporting hierarchy. Org chart visualization. Position control. | T076 | B, F, E | [docs/t077.md](docs/t077.md) |
| T078 | Attendance Management | `Attendance` record — per-company. Biometric import. Manual entry. Overtime hours. Late deduction. | T076 | B, E | [docs/t078.md](docs/t078.md) |
| T079 | Shift & Roster Management | `Shift` model. Roster assignment. Shift swap. Overtime rate per shift type. | T078 | B, E | [docs/t079.md](docs/t079.md) |
| T080 | Leave Management | `LeaveType` (10 types). `LeavePolicy` per grade. Balance accrual. `LeaveApplication` with approval. Calendar. Report. | T016, T076 | B, F, E | [docs/t080.md](docs/t080.md) |
| T081 | Payroll — Salary Structure | `SalaryStructure` per employee: basic, allowances, deductions. Pro-rata. Revision history. | T076 | B | [docs/t081.md](docs/t081.md) |
| T082 | Payroll — EPF Calculation | EPF rates: employee 11%, employer 12-13%. Contribution calculation. Form A. Payment file. | T081 | B | [docs/t082.md](docs/t082.md) |
| T083 | Payroll — SOCSO Calculation | SOCSO contribution by wage bracket. Employer + employee share. Monthly return data. | T081 | B | [docs/t083.md](docs/t083.md) |
| T084 | Payroll — EIS Calculation | EIS: 0.2% employer + 0.2% employee, capped. Contribution calculation. Return data. | T081 | B | [docs/t084.md](docs/t084.md) |
| T085 | Payroll — PCB (MTD) Calculation | Monthly Tax Deduction per LHDN MTD schedule. Resident vs non-resident. CP39 data. | T081 | B | [docs/t085.md](docs/t085.md) |
| T086 | Payroll — Tabung Haji & Zakat | Tabung Haji deduction. Zakat deduction. Payslip integration. | T081 | B | [docs/t086.md](docs/t086.md) |
| T087 | Payroll — Payslip Generation | Monthly payroll run: gross → deductions → net pay. Payslip PDF. Email. Bank file (EFT/IBG). GL journal entry. | T081–T086 | B, F, E | [docs/t087.md](docs/t087.md) |
| T088 | Payroll — EA Form & Form E | EA Form: annual employee earnings. PDF per employee. Form E / CP8D: employer annual return. | T087 | B | [docs/t088.md](docs/t088.md) |
| T089 | Claims & Reimbursement | `Claim` model: type, line items, receipt attachment. Approval workflow. Claim limit. Reimbursement via payroll or separate. | T016, T076 | B, E | [docs/t089.md](docs/t089.md) |
| T090 | Recruitment (Basic) | Job requisition → approval. Candidate tracking. Interview scheduling. Offer letter. Onboarding checklist. | T013 | B, E | [docs/t090.md](docs/t090.md) |
| T091 | Performance Appraisal (Basic) | Appraisal cycle. KPI template per designation. Self + manager appraisal. Overall rating. | T076 | B, E | [docs/t091.md](docs/t091.md) |

---

## Phase 8 — Integration, Reporting & Polish

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T092 | LHDN e-Invoicing Integration | MyInvois API: submission, validation, digital signature. QR code on PDF. Bulk submission. Error handling. | T030, T032, T063 | B, E | [docs/t092.md](docs/t092.md) |
| T093 | Advanced Reporting & Dashboards | Report builder. Dashboard: drag-and-drop widgets. Scheduled email. Export: PDF/Excel/CSV. | T025, T026, T027, T028 | F, E | [docs/t093.md](docs/t093.md) |
| T089a | Report Writer Engine | Report definition (JSON), query builder, pivot/cross-tab engine, data aggregation, data source registry. | T009, T021 | B | [docs/t089a.md](docs/t089a.md) |
| T089b | Report Designer UI | Drag-and-drop report builder, field picker, filter builder, chart/pivot config, live preview. | T089a | F, E | [docs/t089b.md](docs/t089b.md) |
| T089c | Report Viewer & Export | Report rendering, drill-down, PDF/Excel/CSV export, scheduled reports, report history. | T089a, T089b | B, F | [docs/t089c.md](docs/t089c.md) |
| T089d | Document Template Engine | Jinja2 template rendering, variable resolution, conditionals, loops, QR/barcode, PDF via WeasyPrint. | T009 | B | [docs/t089d.md](docs/t089d.md) |
| T089e | Document Template Editor | TipTap WYSIWYG editor, variable insertion, conditional/loop blocks, table builder, QR/barcode, live preview. | T089d | F, E | [docs/t089e.md](docs/t089e.md) |
| T089f | Document Template Management | Template CRUD, versioning, per-company, clone, default templates, EN/BM/CN, import/export. | T089d, T089e | B, F | [docs/t089f.md](docs/t089f.md) |
| T094 | Mobile PWA Optimization | Service worker. Install prompt. Touch-optimized. Card view on mobile. Offline data entry queue. | T006 | F, E | [docs/t094.md](docs/t094.md) |
| T095 | Multi-Language (BM + English) | Django i18n. react-intl. BM + English translations. Language switcher. BM templates. | T009 | F, E | [docs/t095.md](docs/t095.md) |
| T096 | Performance Optimization | Django query optimization, Redis caching. React code splitting, virtual scrolling. Lighthouse 90+. | T093 | — | [docs/t096.md](docs/t096.md) |
| T097 | Security Audit | OWASP Top 10. Dependency scan. SQL injection/XSS/CSRF. Rate limiting. Pen testing. | T092 | — | [docs/t097.md](docs/t097.md) |
| T098 | Documentation & User Guide | Developer docs. API reference. User manual. Video tutorials. FAQ. | T099 | — | [docs/t098.md](docs/t098.md) |
| T099 | Graphify Knowledge Graph — Final | Full graphify scan. Knowledge graph JSON + HTML. Module clustering. Audit report. | T096, T097 | — | [docs/t099.md](docs/t099.md) |

---

## Phase 9 — Project Accounting

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T100 | Project Master | Project setup, types (fixed price/T&M/cost-plus), budget, team, status tracking. | T013, T021 | B, F, E | [docs/t100.md](docs/t100.md) |
| T101 | Project Cost Tracking | Labour, materials, subcontractors, equipment — all tagged to project. Cost by category, by period. | T100 | B, F | [docs/t101.md](docs/t101.md) |
| T102 | Progress Billing | % completion, milestone billing, retention deduction. Revenue recognition. Interim certificates. | T100, T032 | B, E | [docs/t102.md](docs/t102.md) |
| T103 | Retention Money | Retention tracking (5-10%), DLP, release, aging. GL entries for retention receivable/payable. | T102 | B, E | [docs/t103.md](docs/t103.md) |
| T104 | Project P&L & Reporting | Project profitability, budget vs actual, margin analysis, CPI/SPI/EAC metrics. | T100, T101, T102 | B, F | [docs/t104.md](docs/t104.md) |
| T105 | Change Order Management | Scope changes, cost impact, client approval. Budget/contract update on approval. | T100 | B, E | [docs/t105.md](docs/t105.md) |

---

## Phase 10 — Property Management (Reference Industry Module)

| ID | Task | Description | Depends | Tests | Detail |
|---|---|---|---|---|---|
| T200 | Property Register | Property portfolio, types, units, amenities, valuations. Core entity for property management. | T009b, T013 | B, F, E | [docs/t200.md](docs/t200.md) |
| T201 | Tenant Management | Tenant master, screening, documents, history, tenant portal. | T200 | B, F, E | [docs/t201.md](docs/t201.md) |
| T202 | Lease Management | Lease creation, terms, renewal, termination, rent escalation, stamp duty. | T200, T201 | B, E | [docs/t202.md](docs/t202.md) |
| T203 | Rent Invoicing | Monthly rent invoicing, late fees, payment allocation, rent roll. GL integration. | T202, T032 | B, E | [docs/t203.md](docs/t203.md) |
| T204 | Utility Billing | Meter reading, billing by formula, common area allocation, utility revenue GL. | T200, T203, T036e | B, E | [docs/t204.md](docs/t204.md) |
| T205 | Maintenance Requests | Tenant requests, assignment to team/vendor, tracking, SLA, satisfaction rating. | T200, T036d | B, E | [docs/t205.md](docs/t205.md) |
| T206 | Collections | Outstanding tracking, dunning letters, legal action, bad debt write-off. | T203 | B, E | [docs/t206.md](docs/t206.md) |
| T207 | Property Reports | Rent roll, occupancy, collection rate, arrears, property P&L, utility consumption. | T200, T202, T203, T204 | B, F | [docs/t207.md](docs/t207.md) |
| T208 | Property Dashboard | Portfolio overview, occupancy trend, collection performance, maintenance status. | T207 | B, F | [docs/t208.md](docs/t208.md) |

---

## Summary

| Phase | Tasks | Weeks | Focus |
|---|---|---|---|
| 0 | T001–T009f | 1–8 | Scaffolding, Docker, Git, CI/CD, Menu, Layout, Auth, API, Attachments, Plugin Interface, Template Engine, **Data Migration** |
| 1 | T010–T020 | 7–12 | Page Config, Renderer, Builder, Company Architecture, RBAC, Approvals, Numbering, Audit, Notifications |
| 2 | T021–T034b, T089a-f | 13–26 | GL, AP, AR, Bank Reconciliation, Tax/SST, Reports, Budgeting, WIP, Standard Cost, Variance, Cost Centre, Multi-Currency, **Report Writer**, **Document Templates** |
| 3 | T035–T044 | 27–33 | Inter-Company, Fixed Assets (Register, Depreciation, Disposal, Revaluation, Insurance, Capital Allowance, Preventive/Corrective Maintenance, Facility Management, Contracts, Equipment Allocation), Treasury (Cash, Bank, Petty Cash, Forecasting, Loans, Bank Feed, BG/FD, Investment, Multi-Currency Bank) |
| 4 | T045–T056 | 34–39 | Items, Warehouse, Inventory (Movements, Landed Cost, Cost Adjustments, Stock Issues, Stock Receipts), Procurement, PO, GRN, Stock Take, Vendors |
| 5 | T057–T065 | 40–45 | Leads, Opportunities, Customers, Quotation, SO, DO, Logistics (QR), Invoicing, Sales Returns, Consignment, Warranty, RMA |
| 6 | T066–T075 | 46–51 | BOM, Work Centers, Routings, MPS, MRP, Work Orders, QC, Product Costing, Overhead Absorption, Cost Classification, Marginal Costing |
| 7 | T076–T091 | 52–60 | Employees, Attendance, Leave, Payroll (EPF/SOCSO/EIS/PCB/TH/Zakat), Claims, Recruitment, Performance |
| 8 | T092–T099 | 61–64 | e-Invoicing, Dashboards, PWA, i18n, Performance, Security, Docs, Graphify |
| 9 | T100–T105 | 65–68 | Project Master, Cost Tracking, Progress Billing, Retention, Project P&L, Change Orders |
| 10 | T200–T208 | 69–73 | Property Management (Reference Industry Module): Property Register, Tenants, Leases, Rent Invoicing, Utility Billing, Maintenance, Collections, Reports, Dashboard |

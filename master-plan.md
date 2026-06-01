# pyERP — Master Plan

> Full-stack ERP for Malaysian businesses: Financial, Assets, Treasury, SCM, CRM, MRP, HRM.

---

## 1. Tech Stack & Architecture

### Backend

| Layer | Technology | Rationale |
|---|---|---|
| Web framework | **Django 5.x** | ORM, admin, auth, permissions, migrations, mature ecosystem |
| API layer | **Django Ninja** (FastAPI-style syntax, native Django integration) | OpenAPI auto-docs, async views, Pydantic validation — all within Django. Avoids split-process complexity. |
| Database | **PostgreSQL 16** | JSONB for flexible schemas, full-text search, strong ACID |
| Task queue | **Celery + Redis** | Async jobs: report generation, email, bank feeds, e-invoice submission |
| File storage | **MinIO** (S3-compatible) or local FS | Document attachments, invoice PDFs, employee files |
| Auth | **JWT** (djangorestframework-simplejwt) | Token-based auth for React SPA + future mobile app |
| Search | **PostgreSQL full-text** initially, **Elasticsearch** later | Multilingual search, document indexing |

### Frontend

| Layer | Technology | Rationale |
|---|---|---|
| UI framework | **React 19** with **TypeScript** | Component library, type safety |
| Styling | **TailwindCSS 4** | Responsive utilities; enforces no-horizontal-scroll at utility level |
| State management | **TanStack Query** (server state) + **Zustand** (client state) | Avoid Redux boilerplate for an ERP |
| Table/Grid | **AG Grid** (community) or **TanStack Table** | High-performance server-side pagination, sorting, filtering |
| Forms | **React Hook Form** + **Zod** validation | Complex ERP forms with nested line items |
| Charts | **Recharts** or **Apache ECharts** | Financial dashboards, analytics |
| PDF rendering | **React-PDF** client-side + **WeasyPrint** server-side | Invoices, payslips, reports |
| Build | **Vite** | Fast HMR, optimized production builds |

### Infrastructure (Production)

| Layer | Technology |
|---|---|
| Deployment | Docker Compose → Kubernetes later |
| Reverse proxy | Nginx |
| Monitoring | Sentry (errors), Prometheus + Grafana (metrics) |
| CI/CD | GitHub Actions |

### Architecture Decision: Django Ninja (not separate FastAPI)

- **Single process**: Django ORM, admin, and API in one deployable — no need for inter-service auth or duplicated models.
- **FastAPI syntax**: `@router.get("/items/{id}")` with Pydantic schemas.
- **Auto OpenAPI**: `/api/docs` Swagger UI baked in.
- If we ever need a separate high-performance service, migrate specific endpoints to standalone FastAPI later — the schema definitions are reusable Pydantic models.

---

## 2. Multi-Company Architecture

### Master Data: Global + Assignment
- Master records (Item, Customer, Vendor, Employee, COA) are stored **once globally** — no `company_id` FK
- Junction tables (`ItemCompany`, `CustomerCompany`, `VendorCompany`, `EmployeeCompany`, `AccountCompany`) assign master data to companies
- Per-company overrides on junction tables (selling price, credit limit, reorder level, etc.)
- Users see only master data assigned to their active company

### Transactions: Per-Company
- All transaction tables (invoices, POs, journal entries, stock movements) have `company_id` FK
- Always filtered by the user's active company
- Company Switcher in header allows switching between accessible companies

### Company Group Structure
- `Company.parent FK` → self-referencing for group hierarchy
- `Company.is_group` flag for group-level companies
- Inter-company transactions auto-post to both companies
- Consolidation report eliminates inter-company balances at group level

### User-Company Access
- `UserCompany` junction table (user can access multiple companies)
- `is_default` flag for default company on login
- Company Switcher dropdown in header

---

## 3. UI/UX Architecture — No Horizontal Scroll Mandate

### Strategy

- **CSS rule enforced globally**: `html, body { overflow-x: hidden; max-width: 100vw; }`
- **Tailwind container pattern**: `w-full max-w-full overflow-x-hidden` on all layout wrappers
- **Responsive breakpoints**: `sm`(640), `md`(768), `lg`(1024), `xl`(1280), `2xl`(1536)
- **Mobile-first**: default styles for mobile, `md:` / `lg:` / `xl:` prefixes for desktop enhancements
- **Tables**: Horizontal scroll **only inside a bounded container** with `overflow-x-auto` + sticky columns — never on the viewport itself
- **Sidebar**: Collapsible on mobile (hamburger), persistent flyout on desktop (full-height, no push-scroll)
- **Modals & drawers**: `max-h-screen`, `overflow-y-auto`, `max-w-[calc(100vw-2rem)]` — constrained to viewport
- **Testing**: Every page tested at 375px (iPhone SE), 768px (iPad), and 1440px (desktop) — horizontal overflow = bug

---

## 4. Module Breakdown

### Module A: Financial Management

| Sub-module | Key Features |
|---|---|
| **Chart of Accounts** | Hierarchical numbering, multi-company, MFRS-compliant categories, IS/BS segregation |
| **General Ledger** | Double-entry, journal approval workflow, auto-reversing entries, period lock, trial balance, multi-currency |
| **Accounts Payable** | Supplier invoices, 3-way match (PO-GR-IR), payment runs, creditor aging, SST input tax tracking |
| **Accounts Receivable** | Customer invoices, credit notes, debtor aging, dunning letters, SST output tax |
| **Bank Reconciliation** | Statement import (CSV/OFX), auto-match rules, unreconciled items report |
| **Fixed Assets** | Asset register, depreciation (SLM, RBM), disposal, capital allowance (Schedule 3), revaluation, insurance |
| **Preventive Maintenance** | Time/usage-based schedules, auto-generate WOs, calendar, checklist, internal team or vendor |
| **Corrective Maintenance** | Breakdown repair, WO lifecycle, downtime tracking, root cause, cost tracking, spare parts |
| **Facility Management** | Facility register, utility metering, cost allocation, building maintenance, compliance tracking |
| **Maintenance Contracts** | Contract management, SLA tracking, vendor performance, renewal alerts |
| **Equipment Allocation** | Equipment to projects, usage logging, cost per hour, rental vs owned |
| **Financial Reporting** | P&L, Balance Sheet, Cash Flow, Trial Balance, TB mapping, multi-period comparison |
| **Budgeting** | Departmental budgets, variance analysis, budget vs actual |
| **Tax (SST)** | SST-02 return preparation, tax codes per item/service, taxable/non-taxable classification, exemption tracking |
| **Withholding Tax** | WHT on contractor/royalty/interest payments, auto-calculate, GL entries, certificates, monthly remittance (CP37) |
| **Recurring Journals** | Monthly prepayments, accruals, scheduled journal generation via Celery |
| **Budgeting** | Departmental budgets, budget vs actual, variance analysis, budget alerts |
| **GL Account Mapping** | Configurable account mapping per company (no hardcoded accounts) |
| **Aging Buckets** | Company-configurable aging periods for AR/AP reports |
| **Audit Trail** | Immutable transaction log, user-action journal, change tracking on all master data |

### Module B: Treasury

| Sub-module | Features |
|---|---|
| **Cash Management** | Multi-bank-account ledger, petty cash, cash position dashboard |
| **Cash Flow Forecasting** | Projected inflows/outflows from AP/AR, manual adjustments |
| **Loan Management** | Term loans, overdrafts, revolving credit, interest accrual, repayment schedules |
| **Bank Integration** | Bank feed API (future), manual statement import, auto-reconciliation |

### Module C: Supply Chain Management (SCM)

| Sub-module | Features |
|---|---|
| **Item Master** | SKU, UOM, barcode, categories, tax code, cost method (FIFO/weighted avg), reorder levels |
| **Procurement** | Purchase requisition → RFQ → PO, approval matrix, budget check |
| **Goods Receiving** | GRN, partial receipt, QC inspection, lot/serial tracking |
| **Inventory** | Stock movements, stock transfer, stock take/cycle count, valuation reports, negative stock guard |
| **Warehousing** | Multi-warehouse, bin/location management, picking & putaway |
| **Vendor Management** | Vendor master, performance scoring, purchase history |
| **Landed Cost Adjustments** | Freight, insurance, customs duty allocation. Three methods: value, quantity, weight |
| **Cost Adjustments** | Manual unit cost correction, stock ledger update, GL entries |
| **Stock Issues** | Non-trading items (maintenance, packaging, consumables). GL debits expense |
| **Stock Receipts** | Non-purchase receipts (returns, production output, opening stock, donations) |

### Module D: Customer Relationship Management (CRM)

| Sub-module | Features |
|---|---|
| **Lead Management** | Lead capture, source tracking, qualification, conversion to customer |
| **Opportunity Pipeline** | Kanban stages, probability %, expected value, activity timeline |
| **Customer Master** | Contact persons, addresses, credit limit, payment terms, SST registration number, tax code defaults |
| **Sales Quotation** | Multi-line items, discount matrix, validity dates, convert-to-order |
| **Sales Order** | Order fulfilment tracking, backorder handling, delivery schedule |
| **Delivery & Invoicing** | DO generation, invoice from DO, consolidated invoicing |
| **After-Sales** | RMA, service tickets, warranty tracking, customer portal (future) |
| **Sales Returns** | Return authorisation, inspect, credit note, stock adjustment, write-off |
| **Consignment Sales** | Goods on consignment, settlement on sell-through, return of unsold |
| **Product Warranty** | Warranty by serial number, claims, expiry alerts, cost provision |
| **Logistics** | Pick list, sorting, loading plan, delivery confirmation, QR code scanning, GPS |

### External Collaboration Portals

| Portal | Features |
|---|---|
| **Client Portal** | Document view, payment, support tickets, delivery tracking, messaging, account balance, PWA |
| **Supplier Portal** | PO view, invoice submission, RFQ response, delivery updates, payment status, messaging |
| **Portal Security** | Internal/external isolation, entity-scoped data, cross-client/supplier prevention, separate JWT |

### Module E: Manufacturing Resource Planning (MRP)

| Sub-module | Features |
|---|---|
| **Bill of Materials** | Multi-level BOM, phantom items, by-products, revision control, effective dating |
| **Production Planning** | MPS, MRP run (demand-supply netting), capacity load |
| **Work Orders** | WO creation, material issue, labour/time booking, WO completion, partial close |
| **Shop Floor** | Routing/operations, work center management, machine scheduling |
| **Quality Control** | Inspection plans, QC results recording, non-conformance tracking |
| **Costing** | Standard cost, actual cost, variance analysis (material, labour, overhead) |
| **Overhead Absorption** | Predetermined rates, five absorption methods, over/under absorption |
| **Cost Classification** | Direct vs indirect cost breakdown, cost structure per item |
| **Marginal Costing** | Contribution margin, break-even analysis, CVP, absorption vs marginal |

### Module F: Human Resource Management (HRM)

| Sub-module | Features |
|---|---|
| **Employee Master** | Personal data, employment history, emergency contacts, document vault, bank details |
| **Organization Structure** | Departments, designations, grades, reporting hierarchy (org chart) |
| **Attendance** | Clock-in/out, shift roster, overtime calculation, integration with biometric devices |
| **Leave Management** | Leave types (annual, sick, hospitalisation, maternity, paternity, unpaid, Haj, compassionate), leave policy per grade, balance accrual, approval workflow |
| **Payroll** | Salary structure (basic, allowances, deductions), **EPF** (employee 11% / employer 12-13%), **SOCSO** (wage-bracket contribution), **EIS** (0.2% each), **PCB** (MTD schedule), **Tabung Haji**, **Zakat**, payslip generation, bank file (EFT), EA Form, Form E |
| **Claims** | Mileage, travel, medical, overtime claims, approval workflow, receipt attachments |
| **Recruitment** | Job requisition, candidate pipeline, interview scheduling, offer letter generation |
| **Performance** | Appraisal cycles, KPI templates, 360-degree feedback |

### Module G: System Administration

| Sub-module | Features |
|---|---|
| **User & Role Management** | RBAC with fine-grained permissions, module-level access, field-level security |
| **Dynamic Menu System** | Database-driven menu tree, role-menu access control, admin menu management |
| **Company Setup** | Multi-company capable, company profile, financial year, base currency (MYR) |
| **Numbering Series** | Configurable prefixes/ranges for all document types |
| **Approval Workflows** | Configurable multi-level approval for POs, invoices, leave, claims |
| **Confirm Dialog** | Standardized confirmation for all CRUD actions, single reusable component |
| **Dynamic Page Config** | Database-driven page configuration. All forms, lists, detail pages rendered from config. Visual page builder. Zero code to add new fields. |
| **Document Attachments** | Global attachment service — any record can have file attachments (PDF, images, documents) |
| **Notifications** | In-app, email, PWA push, approval reminders, email approve/reject links |
| **Internal Messaging** | Slack-like channels, DMs, threads, file attachments, link previews, system messages, @mentions, search |
| **Data Import/Export** | Bulk import templates (Excel/CSV), data export for audit |
| **Audit Log** | Who did what, when, and from which IP |
| **Advanced Audit** | Bulk ops, login/logout, export tracking, config changes, file audit, approval linkage, retention policy, export, dashboard |

---

## 4a. Industry Modules (Extensible Platform)

pyERP is a **modular ERP platform**. Core modules are always installed. Industry-specific modules are pluggable Django apps.

### Platform Architecture
```
Industry Modules (pluggable)
├── Property Management (T200-T208) — first reference
├── Hotel Management (future)
├── Retail Chain (future)
├── Plantation (future)
└── Utilities (future)

Core Modules (always installed)
├── Finance, Assets, Facility, HRM, SCM, CRM, MRP

Platform Services
├── Auth, RBAC, Menu, Page Config, Workflow, Notifications
├── Concurrency, Multi-Company, Audit, Attachments
├── Module Plugin Interface (T009b)
└── Industry Template Engine (T009c)
```

### How Industry Modules Extend Core

| Core Module | Extension API | What Industry Modules Can Do |
|---|---|---|
| **Finance** | Create JE, post to GL, create invoice, create payment | Any industry can create financial transactions |
| **Asset Management** | Register asset, track depreciation, create maintenance WO | Any industry can manage assets |
| **Facility Management** | Register facility, track utilities, schedule maintenance | Any industry can manage facilities |
| **HRM** | Manage employees, run payroll, track attendance | Any industry can manage workforce |
| **SCM** | Manage inventory, create PO/GRN, track stock | Any industry can manage inventory |
| **CRM** | Manage customers, track leads, create quotations | Any industry can manage customers |

### Adding a New Industry Module

1. Create Django app: `apps/{industry_name}/`
2. Register with platform (T009b): `registry.register_module(MODULE_CONFIG)`
3. Use core module APIs for common operations
4. Add menu items via dynamic menu (T005)
5. Add page configs via page config system (T010)
6. Add workflows via approval workflow system (T016)
7. Add GL accounts via GL account mapping (T029c)
8. Create industry template (T009c) for easy deployment

### Module Plugin Interface (T009b)
- Module registration with config
- Signal bus for inter-module communication
- Dependency management
- Activation/deactivation

### Industry Template Engine (T009c)
- JSON-based templates for each industry
- Templates configure: menus, page configs, workflows, GL accounts, seed data
- Install template → platform configured for that industry

---

## 4b. Property Management (Reference Industry Module)

| Sub-module | Features |
|---|---|
| **Property Register** | Property portfolio, types (residential/commercial/industrial), units, amenities, valuations |
| **Tenant Management** | Tenant master, screening, documents, history, tenant portal |
| **Lease Management** | Lease creation, renewal, termination, rent escalation, stamp duty |
| **Rent Invoicing** | Monthly rent invoicing, late fees, payment allocation, rent roll |
| **Utility Billing** | Meter reading, billing by formula, common area allocation |
| **Maintenance Requests** | Tenant requests, assignment, tracking, SLA, satisfaction rating |
| **Collections** | Outstanding tracking, dunning letters, legal action, bad debt write-off |
| **Reports** | Rent roll, occupancy, collection rate, arrears, property P&L |
| **Dashboard** | Portfolio overview, occupancy trend, collection performance |

### Future Industry Modules

| Industry | Key Features | Core Modules Used |
|---|---|---|
| **Hotel (Hospitality)** | Room management, booking engine, rate management, housekeeping, guest management, F&B POS | Finance, HRM, Facility, SCM |
| **Retail Chain** | POS, multi-store inventory, promotions, loyalty, e-commerce integration | SCM, Finance, CRM |
| **Plantation** | Crop management, harvest tracking, yield calculation, estate management, worker management | SCM, HRM, Asset, Finance |
| **Utilities** | Meter reading, billing, consumption tracking, tariff management, disconnection | Facility, Finance, CRM |

---

## 4c. Report Writer & Document Templates

### Report Writer (T089a-T089c)

User-definable report writer with drag-and-drop designer, pivot/cross-tab analysis, and export capabilities.

| Feature | Description |
|---|---|
| **Report Designer** | Drag-and-drop: select data source → pick fields → add filters → group → sort → pivot → charts |
| **Data Sources** | GL, AP, AR, Inventory, Sales, Purchases, Payroll, Fixed Assets, Projects |
| **Pivot/Cross-tab** | Matrix reports (departments × months, suppliers × aging buckets) |
| **Charts** | Bar, line, pie, scatter, area — built with Recharts |
| **Export** | PDF (WeasyPrint), Excel (openpyxl), CSV |
| **Scheduled Reports** | Daily/weekly/monthly email delivery via Celery |
| **Drill-down** | Click row to see detail records |

### Document Templates (T089d-T089f)

WYSIWYG template editor for business documents using TipTap + Jinja2 + WeasyPrint.

| Feature | Description |
|---|---|
| **Template Editor** | TipTap WYSIWYG: text, tables, images, variables, conditionals, QR/barcodes |
| **Template Variables** | Jinja2 syntax: {{variable}}, {{#if}}, {{#each}}, formatting filters |
| **Document Types** | Invoice, Quotation, PO, DO, Credit Note, Receipt, Payslip, Statement |
| **Multi-Language** | BM and English template sets per document type |
| **Per-Company** | Each company can have its own custom templates |
| **Version Control** | Track changes, compare versions, rollback |
| **Default Templates** | 24 seeded templates (8 types × 3 languages: EN, BM, CN) |

---

## 4d. Data Migration

CSV-based data migration with guided wizard for go-live.

| Feature | Description |
|---|---|
| **CSV Import Engine** | Upload, column mapping (auto/manual), validation, bulk import, rollback |
| **Validation Engine** | Required, unique, type, FK, business rules, format, duplicate detection |
| **Migration Wizard** | 7-step guided process: GL, AP, AR, inventory, assets, review, confirm |
| **Import Templates** | 7 downloadable CSV templates (COA, items, customers, vendors, employees, assets, rates) |
| **Opening Balances** | GL trial balance, AP/AR open invoices, inventory opening stock, asset opening balances |
| **Transaction Migration** | Pending POs/SOs, historical journals/invoices (optional) |
| **Fresh Start Option** | Import master data + opening balances only (recommended) |
| **Full Migration Option** | Import everything including historical transactions |
| **Rollback** | Undo any import if errors found |

---

## 5. Malaysian Compliance Checklist

| # | Requirement | Where Implemented |
|---|---|---|
| 1 | **SST rate engine** (Sales 5-10%, Service 6%) — taxable period, SST-02 return | Module A (AR/AP/Tax) |
| 2 | **SST registration number** on invoices, credit notes, debit notes | Module A, D |
| 3 | **Input tax** tracking & claimable classification | Module A (AP) |
| 4 | **SST exemption** schedules (manufacturing, export, etc.) | Module A (Tax) |
| 5 | **Tourist refund scheme** (optional stretch) | Module D |
| 6 | **EPF contribution** — auto-calc employee 11%, employer 12-13% based on salary bracket | Module F (Payroll) |
| 7 | **SOCSO** — contribution by wage bracket (First & Second Category) | Module F (Payroll) |
| 8 | **EIS** — 0.2% employer + 0.2% employee, capped | Module F (Payroll) |
| 9 | **PCB (MTD)** — monthly tax deduction using LHDN schedule/formula | Module F (Payroll) |
| 10 | **EA Form** generation (annual employee earnings) | Module F (Payroll) |
| 11 | **Form E / CP8D** generation (employer annual return) | Module F (Payroll) |
| 12 | **CP204 / CP204A** tax estimation (corporate) | Module A (Tax) |
| 13 | **e-Invoicing** integration — LHDN MyInvois API (phased mandate: Aug 2024 onwards) | Module A/D (future phase) |
| 14 | **MFRS** financial statement mapping — MFRS 101, 102, 116, etc. | Module A (GL/Reporting) |
| 15 | **MYR** as base currency, multi-currency with exchange gain/loss | Module A/B |
| 16 | **Bahasa Malaysia** & English UI, BM document templates | System-wide i18n |
| 17 | **GST** historical data support (for companies with legacy periods before 2018) | Module A (optional) |
| 18 | **Withholding tax** (contract payments to non-residents, royalty, interest) | Module A (AP) |
| 19 | **Capital allowance** (Schedule 3 ITA 1967) — initial, annual, notional allowance | Module A (Fixed Assets) |
| 20 | **Tabung Haji / Zakat** payroll deductions | Module F (Payroll) |

---

## 6. Data Model — Core Entities

```
Core:
  Company, Branch, FinancialYear, FiscalPeriod, Currency, ExchangeRate
  Menu, MenuRole (dynamic menu system)

Financial:
  ChartOfAccount, JournalEntry, JournalEntryLine, AccountPeriod, TaxCode, TaxRate
  Supplier, Customer, SupplierInvoice, CustomerInvoice, InvoiceLine
  Payment, PaymentAllocation, BankAccount, BankStatement, BankStatementLine
  FixedAsset, FixedAssetCategory, DepreciationSchedule, DepreciationEntry

SCM:
  Item, ItemCategory, UnitOfMeasure, ItemUOM, Warehouse, BinLocation
  PurchaseRequisition, PurchaseOrder, POLine, GoodsReceiptNote, GRNLine
  StockMovement, StockLedger, StockTake, StockTakeLine

CRM:
  Lead, Opportunity, OpportunityStage, SalesQuotation, SalesOrder, SalesOrderLine
  DeliveryOrder, DeliveryOrderLine

MRP:
  BOM, BOMLine, Routing, WorkCenter, WorkOrder, WorkOrderOperation
  ProductionPlan, MaterialRequirement, QCPlan, QCCheck

HRM:
  Employee, Department, Designation, Grade, SalaryStructure
  Attendance, LeaveType, LeavePolicy, LeaveApplication, LeaveBalance
  PayrollPeriod, PayrollRun, PayRunDetail, Payslip, StatutoryContribution

Admin:
  User, Role, Permission, Menu, MenuRole, ApprovalWorkflow, ApprovalStep, ApprovalRequest
  NumberingSeries, Notification, AuditLog
```

---

## 7. Build Phases & Milestones

### Phase 0 — Scaffolding & Foundation (Week 1-4)

| Task | Description |
|---|---|
| T001 | Project Initialization — Django + React+Vite+TS+TailwindCSS scaffolded |
| T002 | Docker Compose Dev Environment — PostgreSQL, Redis, Django, React, MinIO |
| T003 | Git Repository & Graphify Setup — .gitignore, pre-commit hooks, knowledge graph |
| T004 | CI/CD Pipeline — Ruff, Black, mypy, pytest, Vitest, Playwright |
| T005 | Dynamic Menu System — Menu model, seed data, API, Menu-Role junction |
| T006 | Responsive Layout Shell — Sidebar + header + content, no horizontal scroll |
| T007 | Confirm Dialog & Core UI Components — Reusable ConfirmDialog, useConfirm() hook |
| T008 | Authentication System — Custom User model, JWT, login/logout/forgot/reset |
| T009 | API Layer Foundation — Django Ninja setup, Swagger, CRUD pattern, pagination |

### Phase 1 — Core Platform (Week 5-8)

| Task | Description |
|---|---|
| T010 | Page Config Engine — PageConfig + PageConfigField models, admin CRUD, API endpoints |
| T011 | Dynamic Page Renderer — generic React component rendering forms/lists from database config |
| T012 | Visual Page Builder UI — drag-and-drop field placement, live preview, config save |
| T013 | Company & Financial Year Setup |
| T014 | Role-Based Access Control (RBAC) — roles, permissions, Menu-Role linking |
| T015 | User Management UI — user CRUD, role assignment, admin password reset |
| T016 | Approval Workflow Engine — generic multi-level approval, reusable across modules |
| T017 | Numbering Series Engine — configurable prefixes, date components, running numbers |
| T018 | Audit Log System — immutable change tracking on all models |
| T019 | Notification Framework — in-app notifications + email, Celery dispatch |
| T020 | Django Admin Customization — custom admin site, company filtering, role restrictions |

### Phase 2 — Financial Foundation (Week 9-16)

| Task | Description |
|---|---|
| T021 | Chart of Accounts — hierarchical, MFRS mapping, import from template |
| T022 | Journal Entry CRUD — double-entry, auto-balancing, reference linking |
| T023 | Journal Entry Approval & Posting — workflow, GL posting, reversal |
| T024 | Period Management — open/close periods, year-end close, P&L to retained earnings |
| T025 | Trial Balance Report — GL aggregation, period range, drill-down, export |
| T026 | Profit & Loss Statement — configurable template, multi-period, departmental |
| T027 | Balance Sheet — configurable template, comparative periods, export |
| T028 | Cash Flow Statement — direct & indirect method, auto from cash/bank GL |
| T029 | Tax Codes & SST Engine — tax codes, rates, SST-02 output, exemption tracking |
| T030 | Accounts Payable — Supplier Invoice — CRUD, 3-way match, tax, GL posting |
| T031 | Accounts Payable — Payment Runs — proposal, payment method, allocation |
| T032 | Accounts Receivable — Customer Invoice — CRUD, tax, GL posting |
| T033 | Accounts Receivable — Credit Notes & Collections — credit/debit notes, dunning |
| T034 | Bank Reconciliation — statement import, auto-match, reconciliation report |

### Phase 3 — Fixed Assets & Treasury (Week 17-20)

| Task | Description |
|---|---|
| T035 | Fixed Asset Register — asset categories, purchase tracking, barcode |
| T036 | Depreciation Engine — SLM, RBM, GL integration, forecast |
| T037 | Asset Disposal & Transfer — gain/loss, approval, transfer tracking |
| T038 | Capital Allowance Schedules — Schedule 3 ITA 1967, IA, AA, notional allowance |
| T039 | Cash Management — multi-bank, cash position dashboard |
| T040 | Bank Account Management — setup, balance vs GL, reconciliation |
| T041 | Petty Cash — fund, reimbursements, top-up, cash count |
| T042 | Cash Flow Forecasting — projections, scenario analysis |
| T043 | Loan Management — amortization, interest accrual, repayment tracking |

### Phase 4 — Supply Chain Management (Week 21-26)

| Task | Description |
|---|---|
| T044 | Item Master — SKU, UOM, categories, tax code, cost method, pricing |
| T045 | Unit of Measure (UOM) — conversions, purchase/stock/sales UOM |
| T046 | Multi-Warehouse Setup — warehouses, stock by warehouse |
| T047 | Bin Location Management — aisle/rack/shelf/bin, item-bin assignment |
| T048 | Stock Movements & Ledger — in/out/transfer/adjustment, FIFO/weighted avg, negative stock |
| T049 | Stock Valuation Report — FIFO layers, weighted avg, period-end, aging |
| T050 | Purchase Requisition — CRUD, approval, budget check, convert to RFQ/PO |
| T051 | Request for Quotation (RFQ) — vendor comparison, select winner → PO |
| T052 | Purchase Order — CRUD, copy from PR/RFQ, delivery schedule, approval, print |
| T053 | Goods Receiving (GRN) — against PO, partial receipt, QC hold, lot/serial |
| T054 | Stock Take & Cycle Count — count sheets, variance report, adjustment approval |
| T055 | Vendor Management — vendor master, scoring, purchase history |

### Phase 5 — Customer Relationship Management (Week 27-31)

| Task | Description |
|---|---|
| T056 | Lead Management — capture, source, qualification, convert to customer |
| T057 | Opportunity Pipeline — Kanban, expected value, forecast report |
| T058 | Customer Master — contacts, addresses, credit limit, SST no, 360° view |
| T059 | Sales Quotation — multi-line, discount, tax, convert to order, PDF |
| T060 | Sales Order Management — CRUD, backorder, credit limit check, delivery schedule |
| T061 | Delivery Order — from SO, pick list, partial delivery, DO print |
| T062 | Customer Invoicing — from DO, consolidated, tax, GL posting |
| T063 | After-Sales / RMA — return authorization, inspection, credit note/repair |
| T064 | Customer Portal (Basic) — customer login, view quotes/orders/invoices |

### Phase 6 — Manufacturing Resource Planning (Week 32-38)

| Task | Description |
|---|---|
| T065 | Bill of Materials (BOM) — multi-level, component qty, scrap %, where-used |
| T066 | BOM Revisions & Versioning — revision control, effective date, compare |
| T067 | Work Centers — capacity, cost/hour, calendar/shifts, load chart |
| T068 | Routings & Operations — operation sequence, setup/run time, alternate routing |
| T069 | Master Production Schedule (MPS) — demand forecast, safety stock, rough-cut capacity |
| T070 | MRP Run Engine — netting, lead time offset, planned orders, action messages, pegging |
| T071 | Work Orders — CRUD, material issue, labour booking, completion, cost accumulation |
| T072 | Shop Floor Execution — work center queue, operation clocking, scrap/rework |
| T073 | Quality Control Plans — inspection points, test specs, NC tracking, COA |
| T074 | Product Costing — standard cost roll-up, actual cost, variance analysis |

### Phase 7 — Human Resource Management (Week 39-46)

| Task | Description |
|---|---|
| T075 | Employee Master — personal data, IC no, bank details, document vault |
| T076 | Organization Structure — departments, designations, grades, org chart |
| T077 | Attendance Management — clock-in/out, biometric import, overtime, late deduction |
| T078 | Shift & Roster Management — shift setup, roster assignment, swap request |
| T079 | Leave Management — types, policies, balance, application, approval, calendar |
| T080 | Payroll — Salary Structure — basic, allowances, deductions, pro-rata |
| T081 | Payroll — EPF Calculation — employee 11%, employer 12-13%, Form A |
| T082 | Payroll — SOCSO Calculation — wage bracket, employer + employee share |
| T083 | Payroll — EIS Calculation — 0.2% each, capped |
| T084 | Payroll — PCB (MTD) Calculation — LHDN schedule, resident/non-resident |
| T085 | Payroll — Tabung Haji & Zakat — employee-elected deductions |
| T086 | Payroll — Payslip Generation — payroll run, payslip PDF, bank file, GL entry |
| T087 | Payroll — EA Form & Form E — annual earnings statement, employer return |
| T088 | Claims & Reimbursement — mileage, travel, medical, approval, limit |
| T089 | Recruitment (Basic) — job requisition, candidate tracking, offer letter |
| T090 | Performance Appraisal (Basic) — cycles, KPIs, self + manager appraisal |

### Phase 8 — Integration, Reporting & Polish (Week 47-52)

| Task | Description |
|---|---|
| T091 | LHDN e-Invoicing Integration — MyInvois API, QR code, bulk submission |
| T092 | Advanced Reporting & Dashboards — report builder, widgets, scheduled email |
| T093 | Mobile PWA Optimization — service worker, offline, touch interactions |
| T094 | Multi-Language (BM + English) — i18n, translations, BM templates |
| T095 | Performance Optimization — query optimization, caching, code splitting, Lighthouse 90+ |
| T096 | Security Audit — OWASP Top 10, dependency scan, penetration testing |
| T097 | Documentation & User Guide — developer docs, user manual, video tutorials |
| T098 | Graphify Knowledge Graph — Final — full scan, HTML + JSON, audit report |

---

## 8. Key Architectural Decisions

| Decision | Choice | Why |
|---|---|---|
| Monolith vs Microservices | **Modular Monolith first** | ERP modules are tightly coupled. Split into services only when scaling demands it. Django apps enforce module boundaries. |
| REST vs GraphQL | **REST (Django Ninja)** | Simpler for ERP CRUD; React Query handles caching well. GraphQL can be added later for dashboards. |
| Multi-tenancy | **Shared database, global master data + row-level transactions** | Master data (items, customers, vendors, employees, COA) is global with company assignment via junction tables. Transactions are per-company (company_id FK). Company group hierarchy for consolidation. |
| Menu system | **Database-driven, role-linked** | No code changes needed to add new menu items. RBAC controls visibility per role. |
| Page rendering | **Metadata-driven UI via PageConfig tables** | One generic React component renders any page from database config. Add/change fields by inserting records — no code changes. Visual page builder for non-technical users. |
| Confirmation dialogs | **Single reusable `useConfirm()` hook** | Every CRUD action goes through one confirmation component. Zero repetition across modules. |
| i18n approach | **Django's built-in `i18n` + `gettext`** for backend, **react-intl** or **i18next** for frontend | Support BM + English at minimum; template switching for Chinese. |
| PDF generation | **WeasyPrint (server-side)** for invoices, payslips, reports | Pixel-perfect PDFs from HTML/CSS templates; no browser dependency. |
| Real-time | **No WebSocket initially** | ERP does not need real-time. Add Django Channels if live dashboard or notifications become critical. |
| Mobile app | **PWA first**, React Native later | PWA gives instant mobile access; offline-capable with service workers. |

---

## 9. Conventions & House Rules

- **Python**: Type hints everywhere. mypy strict mode on new code.
- **Django**: Fat models, thin views. Business logic in `services.py` per app, never in views.
- **API**: All endpoints return JSON via Django Ninja schemas. No template-rendered pages outside admin.
- **React**: One component per file. Colocate styles with Tailwind classes. No CSS files except global resets.
- **Confirmation dialogs**: Every create/update/delete/post/void action uses `useConfirm()` hook. No exceptions. No `window.confirm()`.
- **Page config**: All forms and lists rendered from `PageConfig` + `PageConfigField` tables. Never hardcode form fields in React. Use `DynamicFormPage` / `DynamicListPage` components.
- **Commits**: Conventional Commits (`feat:`, `fix:`, `chore:`). Squash-merge to `main`.
- **Testing**: `pytest` for backend. `Vitest` for frontend unit. `Playwright` for E2E. Critical paths require tests before merging.
- **Branch naming**: `feat/description`, `fix/description`, `phase-N/description`
- **Environment**: `.env` for secrets, `.env.example` tracked. 12-factor config via `django-environ`.

---

## 10. Cost Accounting Module (Manufacturing)

| Sub-module | Features |
|---|---|
| **WIP Accounting** | Work-in-Progress cost tracking, transfer to finished goods, WIP valuation |
| **Standard Costing** | Standard cost per item, roll-up from BOM + routing, revision control |
| **Variance Analysis** | Material price/usage, labour rate/efficiency, overhead spending/volume variances |
| **Cost Centre Accounting** | Cost centres by department, cost allocation, departmental P&L |

## 11. Project Accounting Module (Project-Based Companies)

| Sub-module | Features |
|---|---|
| **Project Master** | Project types (fixed price/T&M/cost-plus), budget, team, status |
| **Project Cost Tracking** | Labour, materials, subcontractors, equipment tagged to project |
| **Progress Billing** | % completion, milestone billing, retention deduction, revenue recognition |
| **Retention Money** | Retention tracking, DLP, release, aging, GL entries |
| **Project P&L & Reporting** | Profitability, budget vs actual, CPI/SPI/EAC metrics |
| **Change Order Management** | Scope changes, cost impact, client approval, budget update |

## 12. Task Documentation Structure

```
pyERP/
├── master-plan.md          ← this file
├── tasklists.md            ← summary index: T001-T098
├── AGENTS.md               ← AI agent instructions
└── docs/
    ├── t001.md             ← task detail
    ├── t002.md
    ├── ...
    └── t099.md
```

Each task detail file (`docs/txxx.md`) contains:
- **What Is Being Built**: business purpose and feature scope
- **How It Will Be Built**: backend models/services/APIs, frontend components/hooks
- **Deliverables Checklist**: specific checkable items
- **Success Criteria**: measurable acceptance criteria
- **Tests**: Pytest (backend), Vitest (frontend unit), Playwright (E2E) with test file paths
- **Test Results**: table for recording run results

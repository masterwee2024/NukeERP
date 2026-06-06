---
name: report-engine
description: >-
  pyERP report engine — standardised pipeline for every report. Report registry
  in DB (ReportDefinition + ReportParameter), pre-aggregated AccountPeriodBalance
  for financial reports, mixed SQL + Python computation, dynamic filter component,
  streaming CSV, async PDF/Excel, drill-anywhere.
license: MIT
compatibility: opencode
---

# Report Engine

## Core Concept

Every report follows the same **five-stage pipeline**:

```
Filters → Compute → Format → Paginate → Output
```

All reports share the same filter UI, the same engine service, the same export formats. The only difference between reports is what's in the `ReportDefinition` registry record — which determines compute method (`sql` or `python`), parameters, and column layout.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       ReportPage (Generic)                  │
│              Route: /app/financial/reports/:reportCode      │
├────────────────────────┬────────────────────────────────────┤
│   Left Panel (30%)     │   Right Panel (70%)               │
│   Drag-resizable       │                                    │
├────────────────────────┼────────────────────────────────────┤
│  ReportFilters         │  ┌─ Toolbar ────────────────────┐ │
│  ┌──────────────────┐  │  │ [Table] [Chart]  [Export ▼]↻│ │
│  │ Period From      │  │  └─────────────────────────────┘ │
│  │ Period To        │  │  ┌─ Filter Badges ────────────┐ │ │
│  │ Accounts (tree)  │  │  │[Period: Jan ×] [Clear All] │ │ │
│  │ Show Zero        │  │  └─────────────────────────────┘ │ │
│  │ [Apply Filters]  │  │  ┌─ Summary Cards ────────────┐ │ │
│  │ [+ Save Preset]  │  │  │Debit   Credit   Balance    │ │ │
│  └──────────────────┘  │  └─────────────────────────────┘ │ │
│                         │  ┌─ Table / Chart ─────────────┐ │ │
│                         │  │ Columns (resizable)         │ │ │
│                         │  │ ▸ Group header (collapsible)│ │ │
│                         │  │   row data...               │ │ │
│                         │  │ ▸ Group header              │ │ │
│                         │  │ Subtotal                    │ │ │
│                         │  │ ======= Grand Total ======= │ │ │
│                         │  │ < Page 1 of 17 >  1-100/1642│ │ │
│                         │  └─────────────────────────────┘ │ │
├────────────────────────┴────────────────────────────────────┤
│  DrillDownModal (on cell click)                              │
└─────────────────────────────────────────────────────────────┘
```

## Report Registry (Database)

### ReportDefinition

Stored in the database — seeded by management command, editable via admin UI.

```python
class ReportDefinition(ConcurrencyModel):
    code = models.SlugField(unique=True)         # "trial_balance"
    name = models.CharField(max_length=200)       # "Trial Balance"
    module = models.CharField(max_length=50)       # "financial", "scm", "crm"
    category = models.CharField(max_length=50)     # "financial_statement", "aging", "tax"
    company_scoped = models.BooleanField(default=True)

    # Computation
    compute_type = models.CharField(
        max_length=20,
        choices=[("sql", "SQL"), ("python", "Python Service")],
    )
    sql_template = models.TextField(blank=True)   # Parametrized SQL (compute_type="sql")
    service_method = models.CharField(             # Dotted path (compute_type="python")
        max_length=300, blank=True, default=""
    )
    pre_aggregated = models.BooleanField(default=False)  # Uses AccountPeriodBalance?
    supports_drill_down = models.BooleanField(default=False)

    # Layout
    has_columns = models.BooleanField(default=True)
    group_field = models.CharField(                # Column key for group headers
        max_length=100, blank=True, default=""
    )
    show_subtotals = models.BooleanField(default=True)
    show_grand_total = models.BooleanField(default=True)
    page_size = models.PositiveIntegerField(default=100)

    # Cache
    cache_ttl_seconds = models.PositiveIntegerField(default=300)
    is_active = models.BooleanField(default=True)
```

### ReportParameter

Defines the filter form for each report. Rendered dynamically by `<ReportFilters>`.

```python
class ReportParameter(ConcurrencyModel):
    PARAM_TYPES = [
        ("date", "Date"),
        ("date_range", "Date Range"),
        ("period", "Period"),
        ("period_range", "Period Range"),
        ("account_multi", "Account Multi-Select"),
        ("account_tree", "Account Tree Select"),
        ("customer_multi", "Customer Multi-Select"),
        ("vendor_multi", "Vendor Multi-Select"),
        ("text", "Text"),
        ("select", "Dropdown"),
        ("multi_select", "Multi Select"),
        ("checkbox", "Checkbox"),
        ("company", "Company"),
        ("comparison", "Comparison Period"),
    ]

    report = models.ForeignKey(
        ReportDefinition, on_delete=models.CASCADE, related_name="parameters"
    )
    key = models.SlugField()                       # "date_from", "account_ids"
    label = models.CharField(max_length=200)
    param_type = models.CharField(max_length=30, choices=PARAM_TYPES)
    required = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    options_source = models.CharField(             # API endpoint for dynamic options
        max_length=300, blank=True, default=""
    )
    validation = models.JSONField(                 # {min, max, pattern, min_length}
        default=dict, blank=True
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = ("report", "key")
```

### ReportExport

Tracks generated exports for async delivery.

```python
class ReportExport(ConcurrencyModel):
    FORMAT_CHOICES = [("csv", "CSV"), ("pdf", "PDF"), ("xlsx", "Excel")]

    report = models.ForeignKey(
        ReportDefinition, on_delete=models.CASCADE, related_name="exports"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="report_exports")
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="report_exports"
    )
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    params = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=[("generating", "Generating"), ("ready", "Ready"), ("failed", "Failed")],
        default="generating",
    )
    file = models.FileField(upload_to="report_exports/%Y/%m/", blank=True)
    error_message = models.TextField(blank=True, default="")
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()  # Auto-cleanup after 7 days
```

## Pre-Aggregation Layer (AccountPeriodBalance)

### The Problem

Scanning `GeneralLedger` — which can grow to millions of rows — every time a user runs a Trial Balance is prohibitively slow.

### The Solution

`AccountPeriodBalance` stores pre-computed period-level balances, updated **synchronously** in the same transaction as every GL posting.

```python
class AccountPeriodBalance(ConcurrencyModel):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="period_balances"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="period_balances"
    )
    period = models.ForeignKey(
        FinancialPeriod, on_delete=models.CASCADE, related_name="account_balances"
    )
    opening_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    opening_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    period_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    period_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    closing_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    closing_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = ("account", "company", "period")
```

### Update Rule

In `posting_service.py`, inside `@transaction.atomic`:

```python
def _update_period_balance(account, company, period, debit, credit):
    bal, _ = AccountPeriodBalance.objects.select_for_update().get_or_create(
        account=account, company=company, period=period,
        defaults={"opening_debit": 0, "opening_credit": 0,
                  "period_debit": 0, "period_credit": 0,
                  "closing_debit": 0, "closing_credit": 0},
    )
    # Opening balance = closing balance of previous period
    # (computed during backfill or on first posting)
    bal.period_debit += debit
    bal.period_credit += credit
    bal.closing_debit = bal.opening_debit + bal.period_debit
    bal.closing_credit = bal.opening_credit + bal.period_credit
    bal.save(update_fields=["period_debit", "period_credit",
                            "closing_debit", "closing_credit", "updated_at", "version"])
```

### Backfill Migration

For existing data, a data migration computes all historical balances from `GeneralLedger`:

```python
def backfill_account_period_balances(apps, schema_editor):
    GL = apps.get_model("financial", "GeneralLedger")
    APB = apps.get_model("financial", "AccountPeriodBalance")
    # Group GL entries by (account, company, period) → aggregate
    # For opening: sum of all GL before period start
    # For period: sum of GL in period
```

### Reports Using Pre-Aggregation

| Report | AccountPeriodBalance? |
|--------|----------------------|
| Trial Balance | Yes |
| P&L | Yes (filtered revenue/expense) |
| Balance Sheet | Yes (filtered asset/liability/equity) |
| Cash Flow | No (uses GL directly for cash movement) |
| Aging | No (uses invoice data, not GL) |

## Computation Layer — SQL vs Python

### Decision Rule

> If a report can be expressed as a single `SELECT ... GROUP BY` (possibly with CTEs/window functions), use **SQL**. If it needs loops, conditionals, merging heterogeneous data sources, or calling external services — use **Python**.

| Report | Method | Reason |
|--------|--------|--------|
| Trial Balance | SQL | Pure aggregation on AccountPeriodBalance |
| P&L | SQL | Same as TB with account_type filter |
| Balance Sheet | SQL | Same as TB with account_type filter |
| Cash Flow | SQL | Set-based from GL, window functions for indirect method |
| Aging (AP/AR) | Python | Dynamic bucket config, date calc per invoice |
| Budget vs Actual | Python | Merges GL + Budget, variance calculations |
| Tax Reports (SST-02) | Python | Tax table lookups, exemption rules |
| Drill-down | Python | Dynamic query built from row context |

### SQL Report Pattern

SQL templates use **Django parameterized queries** — never string interpolation:

```sql
SELECT
    a.code,
    a.name,
    a.account_type,
    ab.opening_debit,
    ab.opening_credit,
    ab.period_debit,
    ab.period_credit,
    ab.closing_debit,
    ab.closing_credit
FROM financial_accountperiodbalance ab
JOIN financial_account a ON a.id = ab.account_id
WHERE ab.company_id = %(company_id)s
  AND ab.period_id BETWEEN %(period_from)s AND %(period_to)s
  {% if account_ids %}
  AND ab.account_id = ANY(%(account_ids)s)
  {% endif %}
ORDER BY a.code
```

SQL engine uses `django.db.connection.cursor.execute(sql, params)` — params dict is always `%(key)s` style, never `$` or positional.

### Python Report Pattern

```python
# apps/financial/services/aging_service.py
def run_aging_report(params: dict, company_id: UUID) -> list[dict]:
    """
    Compute AP aging report with configurable buckets.
    params: { "bucket_days": [30, 60, 90, 120], "vendor_ids": [...], "as_of_date": "2026-06-06" }
    """
    # Fetch open invoices
    invoices = SupplierInvoice.objects.filter(
        company_id=company_id,
        status__in=["approved", "posted"],
        due_date__lte=params["as_of_date"],
    )
    if params.get("vendor_ids"):
        invoices = invoices.filter(vendor_id__in=params["vendor_ids"])

    # Calculate age buckets
    buckets = {}
    for inv in invoices:
        days_overdue = (params["as_of_date"] - inv.due_date).days
        bucket = _find_bucket(days_overdue, params["bucket_days"])
        buckets.setdefault(bucket, {"total": 0, "count": 0, "invoices": []})
        buckets[bucket]["total"] += inv.balance_due
        buckets[bucket]["count"] += 1

    return [{"bucket": k, **v} for k, v in sorted(buckets.items())]
```

The Python service method is referenced in `ReportDefinition.service_method` as `"apps.financial.services.aging_service.run_aging_report"`.

## Report Engine Service

Located at `apps/financial/services/report_service.py` (or respective module).

### Main Methods

```python
class ReportEngine:
    """Central report computation and delivery service."""

    def run(self, report_code: str, params: dict, user: User) -> ReportResult:
        """Full pipeline: validate params → check cache → compute → paginate → format."""
        report = get_report_or_404(report_code, user.company_id)
        self._validate_params(report, params)

        cache_key = self._cache_key(report_code, params, user.company_id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        if report.compute_type == "sql":
            data = self._run_sql(report.sql_template, params, user.company_id)
        else:
            service = import_string(report.service_method)
            data = service(params, user.company_id)

        total = len(data)
        page = self._paginate(data, params.get("page", 1), params.get("page_size", report.page_size))
        formatted = self._format_columns(page, report)

        result = ReportResult(
            columns=self._get_columns(report),
            rows=formatted,
            total_rows=total,
            page=params.get("page", 1),
            page_size=params.get("page_size", report.page_size),
            generated_at=datetime.now(),
            summary=self._compute_summary(data, report),
            group_totals=self._compute_group_totals(data, report),
        )

        cache.set(cache_key, result, report.cache_ttl_seconds)
        return result

    def drill_down(self, report_code: str, row_id: str, params: dict, user: User) -> DetailResult:
        """Return detailed transactions for a summary row."""
        report = get_report_or_404(report_code, user.company_id)
        if not report.supports_drill_down:
            raise ValueError("This report does not support drill-down")
        # Dispatch to report-specific drill-down query or service
        ...

    def export(self, report_code: str, params: dict, fmt: str, user: User) -> ReportExport:
        """Trigger async export. Returns immediately with task status."""
        export = ReportExport.objects.create(...)
        generate_export.delay(export.id, report_code, params, fmt, user.id)
        return export
```

### Cache Strategy

- **Cache key**: `hashlib.md5(f"report:{report_code}:{company_id}:{json.dumps(params, sort_keys=True)}".encode()).hexdigest()`
- **TTL**: Per-report configuration defaulting to 300s (5 minutes)
- **Invalidation**: When a GL entry is posted in a period that affects a report, delete cache keys with matching period prefix
- **No cache for drill-down** — always live (drill-down happens on demand and needs current data)

### Pagination

Always paginate screen results. Default 100 rows per page. Use cursor-based pagination for very large datasets (though pre-aggregation keeps TB/P&L/BS small).

## API Endpoints

All endpoints under `/api/v1/{module}/reports/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `.../reports/` | List available reports for current company |
| `GET` | `.../reports/{code}/parameters/` | Parameter definitions for filter form |
| `GET` | `.../reports/{code}/` | Run report (params in query string) |
| `GET` | `.../reports/{code}/drill-down/` | Drill-down from summary row |
| `POST` | `.../reports/{code}/export/` | Trigger async export (body: {format, params}) |
| `GET` | `.../exports/{export_id}/` | Poll export status, get download URL when ready |

### ReportResult Schema

```python
class ReportResult(Schema):
    columns: list[ColumnDef]       # key, label, type, align, format, width
    rows: list[dict]               # data rows (page only)
    total_rows: int
    page: int
    page_size: int
    generated_at: datetime
    summary: ReportSummary | None  # grand total row
    group_totals: list[GroupTotal] | None

class ColumnDef(Schema):
    key: str
    label: str
    type: str                      # "string", "decimal", "currency", "date", "integer"
    align: str = "left"            # "left", "center", "right"
    format: str = ""               # "decimal_2", "currency_myr", "date_ymd"
    width: str = ""                # CSS width hint

class ReportSummary(Schema):
    row: dict                      # key → aggregated value for each column

class GroupTotal(Schema):
    group_key: str
    group_label: str
    row: dict                      # subtotal row
```

## Filter System (React)

### ReportFilters Component

```tsx
<ReportFilters reportCode="trial_balance" onRun={handleRun} />
```

**Behaviour:**
1. On mount, fetches `GET .../reports/{code}/parameters/`
2. Renders filter form dynamically from parameter definitions
3. Each `param_type` maps to a specific UI widget:

| param_type | UI Widget |
|-----------|-----------|
| `date` | `<input type="date">` |
| `date_range` | shadcn `DatePickerWithRange` |
| `period` | Dropdown of open periods (fetched from API) |
| `period_range` | Two period dropdowns (from/to) |
| `account_tree` | Hierarchical tree with checkboxes |
| `account_multi` | Searchable multi-select |
| `customer_multi` | Searchable multi-select |
| `select` | Standard dropdown |
| `checkbox` | Checkbox |
| `text` | Text input |

4. "Apply Filters" button → serialises all filters to URL query params → calls `onRun(filters)`
5. "Save Preset" → saves current filter combination (stored in localStorage keyed by report + user)
6. "Load Preset" → applies previously saved filter combination

### Shared Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ReportPage` | `pages/reports/ReportPage.tsx` | **Generic** — serves ALL reports via `:reportCode` URL param |
| `ReportFilters` | `components/reports/ReportFilters.tsx` | Dynamic filter form from registry |
| `AccountTreeSelect` | `components/reports/AccountTreeSelect.tsx` | Hierarchical COA picker with checkboxes |
| `PeriodRangeSelect` | `components/reports/PeriodRangeSelect.tsx` | Period from/to picker |
| `ReportTable` | `components/reports/ReportTable.tsx` | Table with sticky header, collapsible groups, column resize, pagination |
| `ReportChart` | `components/reports/ReportChart.tsx` | Recharts stacked bar chart by group |
| `ActiveFilterBadges` | `components/reports/ActiveFilterBadges.tsx` | Removable chips showing active filters |
| `ViewSwitcher` | `components/reports/ViewSwitcher.tsx` | Table/Chart toggle button group |
| `DrillDownModal` | `components/reports/DrillDownModal.tsx` | Modal showing drill-down detail |
| `ExportButtons` | `components/reports/ExportButtons.tsx` | CSV/PDF/Excel export with inline status |
| `FilterPresetManager` | `components/reports/FilterPresetManager.tsx` | Save/load/delete filter presets |

## Output Formats

| Format | Generation | Delivery | Notes |
|--------|-----------|----------|-------|
| Screen | Synchronous | JSON → virtual scroll table | Always paginated |
| CSV | Synchronous (streaming) | `StreamingHttpResponse` | No temp file, no memory overhead |
| PDF | Async (Celery + WeasyPrint) | Notification link → download | Uses Jinja2 HTML template |
| Excel | Async (Celery + openpyxl) | Notification link → download | Styled with headers and formatting |

### CSV Streaming

```python
class ReportCsvStreamer:
    """Stream report data as CSV directly to the client."""

    def stream(self, report_code, params, user):
        report = get_report_or_404(report_code, user.company_id)
        yield self._header_row(report)
        for batch in self._batch_data(report, params, user.company_id, batch_size=1000):
            yield self._data_rows(batch)
```

### PDF Generation

PDF uses WeasyPrint with Jinja2 HTML templates. Async via Celery:

```python
@shared_task(bind=True, max_retries=2)
def generate_report_pdf(self, export_id):
    export = ReportExport.objects.get(id=export_id)
    try:
        data = ReportEngine().run(export.report.code, export.params, export.user)
        html = render_to_string("reports/report_template.html", {
            "report": export.report,
            "data": data,
            "company": export.company,
        })
        pdf = WeasyPrint(html).write_pdf()
        export.file.save(f"{export.report.code}_{export.id}.pdf", ContentFile(pdf))
        export.status = "ready"
        export.generated_at = timezone.now()
        export.save()
        # Notify user
        Notification.objects.create(...)
    except Exception as e:
        export.status = "failed"
        export.error_message = str(e)
        export.save()
```

## Drill-Anywhere

Every number in every report is clickable:

1. User clicks a cell in the report table
2. Frontend calls `GET .../reports/{code}/drill-down/?account_id=X&period_id=Y`
3. Backend returns paginated GL entries for that account+period
4. `DrillDownModal` shows the detail in a scrollable table
5. User can click a GL entry → navigates to the Journal Entry detail page

Implementation:

```python
def drill_down_trial_balance(account_id: UUID, period_id: UUID, company_id: UUID, page=1):
    """Return GL entries for a given account and period."""
    gl_entries = GeneralLedger.objects.filter(
        account_id=account_id,
        period_id=period_id,
        company_id=company_id,
    ).select_related("journal_entry").order_by("date", "created_at")

    total = gl_entries.count()
    page_data = gl_entries[(page - 1) * 50: page * 50]

    return [
        {
            "date": e.date,
            "entry_number": e.journal_entry.entry_number,
            "description": e.journal_entry.description,
            "debit": e.debit,
            "credit": e.credit,
            "balance": e.balance,
            "entry_id": str(e.journal_entry.id),
        }
        for e in page_data
    ], total
```

## URL Convention

| Format | Example | Where |
|--------|---------|-------|
| Dashes | `financial/reports/trial-balance` | URL path and sidebar menu `url` |
| Underscores | `trial_balance` | `ReportDefinition.code` in database |

The `ReportPage` normalizes automatically: `const reportCode = rawCode?.replace(/-/g, "_") || ""`

## ReportTable Props

```tsx
interface ReportTableProps {
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  groupField?: string;
  summary?: Record<string, number> | null;
  groupTotals?: Array<Record<string, unknown>>;
  onDrillDown?: (row: Record<string, unknown>, columnKey: string) => void;
  page?: number;
  pageSize?: number;
  totalRows?: number;
  onPageChange?: (page: number) => void;
}
```

## Report Engine Service — Pagination

The `ReportService.run()` method accepts `page` and `page_size` params and applies them to the query:

- **SQL reports**: wraps the SQL template in a subquery with `LIMIT %(_limit)s OFFSET %(_offset)s`. Also runs a `SELECT COUNT(*)` on the same template for total rows.
- **Python reports**: slices the returned list: `data[(page-1)*page_size : page*page_size]`

The result includes `total_rows`, `page`, and `page_size` fields for frontend pagination controls.

## When to Build a New Report

### Workflow (no frontend code needed)

1. Write SQL template or Python service function
2. Add to `seed_reports.py`: `ReportDefinition` + `ReportParameter` records
3. Add sidebar menu entry to `seed_menus.py`
4. Run `uv run python manage.py seed_reports`
5. Run `uv run python manage.py seed_menus`
6. Run `uv run python manage.py validate_menus`

### Checklist

- [ ] Register `ReportDefinition` in seed data (`apps/financial/management/commands/seed_reports.py`) — use underscores in code
- [ ] Add `ReportParameter` records for every filter the report needs
- [ ] If SQL: write parametrized SQL template, test with varying params
- [ ] If Python: write service function in `apps/{module}/services/{report_name}_service.py`
- [ ] Add data migration if new fields/models are needed
- [ ] **No frontend page needed** — `ReportPage` handles all reports generically
- [ ] Add sidebar menu in `seed_menus.py` — use dashes in URL (e.g. `/app/financial/reports/trial-balance`)
- [ ] Add icon to `SidebarItem.tsx` iconMap if new icon
- [ ] Add service-level unit tests (backend)
- [ ] Add API integration tests (auth, company scoping, pagination)
- [ ] Add drill-down support if applicable
- [ ] Run `validate_menus` after seeding

### Seed Data Pattern

```python
# apps/financial/management/commands/seed_reports.py
def seed_trial_balance():
    report, _ = ReportDefinition.objects.update_or_create(
        code="trial_balance",
        defaults={
            "name": "Trial Balance",
            "module": "financial",
            "compute_type": "sql",
            "sql_template": TRIAL_BALANCE_SQL,
            "pre_aggregated": True,
            "supports_drill_down": True,
            "group_field": "account_type",
            "show_subtotals": True,
            "show_grand_total": True,
        },
    )
    params = [
        ReportParameter(report=report, key="period_from", label="Period From",
                        param_type="period", required=True, sort_order=10),
        ReportParameter(report=report, key="period_to", label="Period To",
                        param_type="period", required=True, sort_order=20),
        ReportParameter(report=report, key="account_ids", label="Accounts",
                        param_type="account_tree", required=False, sort_order=30),
        ReportParameter(report=report, key="show_zero_balances", label="Show Zero Balances",
                        param_type="checkbox", required=False,
                        default_value=False, sort_order=40),
    ]
    for p in params:
        p.save()
```

## Trial Balance (T025) — Reference Implementation

### SQL Template

```sql
SELECT
    a.code,
    a.name,
    a.account_type,
    a.subtype,
    ab.opening_debit,
    ab.opening_credit,
    ab.period_debit,
    ab.period_credit,
    ab.closing_debit,
    ab.closing_credit
FROM financial_accountperiodbalance ab
JOIN financial_account a ON a.id = ab.account_id
WHERE ab.company_id = %(company_id)s
  AND ab.period_id BETWEEN %(period_from)s AND %(period_to)s
  {% if account_ids %}
  AND ab.account_id = ANY(%(account_ids)s)
  {% endif %}
ORDER BY a.code
```

### Parameters

| Key | Label | Type | Required |
|-----|-------|------|----------|
| period_from | Period From | period | Yes |
| period_to | Period To | period | Yes |
| account_ids | Accounts | account_tree | No |
| show_zero_balances | Show Zero Balances | checkbox | No |

### Grouping & Totals

- **Group**: `account_type` (asset, liability, equity, revenue, expense)
- **Subtotals**: Sum of all numeric columns per group
- **Grand total**: Sum of all numeric columns — must equal zero (debits = credits)
- **Zero balance filtering**: If `show_zero_balances=false`, exclude rows where all balance columns are zero

### Route — One Route for All Reports

```tsx
// frontend/src/App.tsx — single route serves every report
<Route path="financial/reports/:reportCode" element={<ReportPage />} />
```

No per-report pages needed. The `reportCode` URL parameter is normalized (dash → underscore) and used for all API calls.

### Page Layout

Every report page renders in `FormPageLayout` with a 30/70 resizable split:

```
Desktop (≥1280px):            Tablet/Mobile:
+--------+---------------+    +------------------+
|Filters | Report        |    | Filters           |
|(30%)   | Toolbar       |    | (collapsible)     |
|        | Badges        |    +------------------+
|        | Summary Cards |    | Report            |
|        | Table/Chart   |    | (full width)      |
|        | Pagination    |    +------------------+
+--------+---------------+
```

**Toolbar** (right panel top):
```
[Table] [Chart]          [Export CSV] [Export PDF] [↻ Refresh]
```

**Filter Badges** (below toolbar):
Shows each active filter as a removable chip. Click × to clear that filter and auto-refresh.

**CRITICAL RULE:** Filter badges must ALWAYS display human-readable values, never raw UUIDs/IDs.
- Period filters resolve UUID → period name via cached API data
- Account filters show count ("3 selected") rather than UUID list
- Boolean filters show "Yes"/"No" rather than raw values

**Summary Cards** (below badges):
Three colored cards: Total Debit, Total Credit, Net Balance. Balance card is green when zero, red otherwise.

**Table Features:**
- Sticky column headers
- Collapsible group rows (groups start collapsed, click to expand)
- Column resize via drag handle on column border
- Pagination: "← Page 1 of 17 →  Showing 1-100 of 1642"
- Currency formatting with locale "en-MY"
- Drill-down on cell click → opens modal with detail entries

**Chart Replacement:**
When ViewSwitcher is set to "Chart", the table is replaced with a Recharts stacked bar chart grouped by `groupField` (e.g. account_type). Each bar shows debit (blue) and credit (amber) segments.

## P&L (T026) — Extension Pattern

Reuses the same TB engine with a WHERE filter:

```sql
WHERE a.account_type IN ('revenue', 'expense')
-- Plus comparison period columns added by param
```

Adds parameter for optional comparative period:

| Key | Label | Type | Required |
|-----|-------|------|----------|
| compare_to | Compare To | comparison | No |

When `compare_to` is set, the engine generates 4 extra columns per row:
- Current period value
- Comparison period value
- Variance (absolute)
- Variance (%)

## Cash Flow (T028) — SQL with Window Functions

Uses `GeneralLedger` directly (not pre-aggregated) because cash flow needs transaction-level classification:

```sql
-- Indirect method: start with net profit, adjust for non-cash items
WITH net_profit AS (
    SELECT SUM(closing_debit - closing_credit) AS amount
    FROM financial_accountperiodbalance
    WHERE account_type = 'equity' AND period_id BETWEEN %(period_from)s AND %(period_to)s
),
-- Cash movement from operating activities
operating AS (
    SELECT gl.date, gl.debit, gl.credit,
           CASE
               WHEN a.account_type = 'current_asset' AND a.subtype != 'cash_and_bank' THEN -(gl.debit - gl.credit)
               WHEN a.account_type = 'current_liability' THEN gl.credit - gl.debit
               ELSE 0
           END AS operating_flow
    FROM financial_general_ledger gl
    JOIN financial_account a ON a.id = gl.account_id
    WHERE gl.company_id = %(company_id)s AND gl.period_id BETWEEN %(period_from)s AND %(period_to)s
)
-- ... combine sections
```

## Implementation Order

| Step | Task | Est. |
|------|------|------|
| 1 | `AccountPeriodBalance` model + migration | 0.5d |
| 2 | Update posting service to update balances | 0.5d |
| 3 | Backfill migration for historical data | 0.5d |
| 4 | `ReportDefinition` + `ReportParameter` + `ReportExport` models | 0.5d |
| 5 | `report_service.py` (run, cache, paginate, format) | 1d |
| 6 | Report API endpoints | 1d |
| 7 | Seed ReportDefinition for TB + P&L + BS | 0.5d |
| 8 | Filter components (ReportFilters, AccountTreeSelect, etc.) | 1d |
| 9 | Trial Balance page | 1d |
| 10 | CSV streaming + PDF/Excel async export | 1d |
| 11 | Drill-down modal | 0.5d |
| 12 | Tests (service unit + API integration + frontend + E2E) | 2d |
| **Total** | | **10d** |

## Conventions

### Display Values — Never Show Raw IDs

When rendering filter values, parameter options, or any reference data:

| Filter Type | Display | Implementation |
|------------|---------|---------------|
| `period` / `period_range` | Period name (e.g. "January 2026") | Resolve UUID via cached periods API |
| `account_tree` / `account_multi` | Count (e.g. "3 selected") | `Array.isArray(v) ? \`${v.length} selected\`` |
| `customer_multi` / `vendor_multi` | Count (e.g. "2 selected") | Same as accounts |
| `checkbox` | "Yes" / "No" | Ternary check |
| `select` | Option label | Must have `options_source` with label/value pairs |
| Raw UUID | NEVER show | Always resolve to a display name |

This applies to **filter badges**, **export filenames**, **page titles**, and **any user-facing text**.

### Naming

| Convention | Example |
|-----------|---------|
| Report code (DB) | `trial_balance`, `profit_and_loss` (underscores) |
| Report URL (sidebar) | `/app/financial/reports/trial-balance` (dashes) |
| Report parameter key | `date_from`, `account_ids`, `show_zero_balances` |
| Service file | `apps/financial/services/report_service.py` |
| Service function | `run_trial_balance(params, company_id)` |
| API file | `apps/financial/api/report_api.py` |
| Frontend page | `pages/reports/ReportPage.tsx` (generic — one for all) |
| Frontend component | `components/reports/ReportTable.tsx` |

### Database

- `AccountPeriodBalance` updated in same transaction as GL posting
- `ReportDefinition` seeded by management command, not hardcoded
- `ReportParameter` sorted by `sort_order` for consistent filter ordering
- `ReportExport` auto-cleans exports older than 7 days (`celery beat` task)
- Company scoping on ALL queries (never show cross-company data)

### Testing

- Service-layer tests: mock SQL execution, test param validation, test pagination boundaries
- API tests: auth, company scoping, parameter validation, drill-down, export trigger
- Frontend tests: filter form rendering (cover each param_type), export button click
- E2E: filter → apply → verify table renders → export → verify download
- Always test with both empty results and large results (pagination edge)

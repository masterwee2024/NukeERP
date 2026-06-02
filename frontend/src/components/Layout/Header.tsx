import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useCompanies } from "@/hooks/useCompanyContext";

interface HeaderProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
  onToggleCollapse: () => void;
}

const breadcrumbs: Record<string, string> = {
  dashboard: "Dashboard",
  financial: "Financial",
  coa: "Chart of Accounts",
  gl: "General Ledger",
  journal: "Journal Entries",
  "trial-balance": "Trial Balance",
  ap: "Accounts Payable",
  invoices: "Invoices",
  payments: "Payment Runs",
  ar: "Accounts Receivable",
  "credit-notes": "Credit Notes",
  "bank-reconciliation": "Bank Reconciliation",
  tax: "Tax / SST",
  reports: "Reports",
  pnl: "Profit & Loss",
  "balance-sheet": "Balance Sheet",
  "cash-flow": "Cash Flow Statement",
  assets: "Fixed Assets",
  register: "Asset Register",
  depreciation: "Depreciation",
  "capital-allowance": "Capital Allowance",
  treasury: "Treasury",
  cash: "Cash Management",
  banks: "Bank Accounts",
  "cash-flow-forecast": "Cash Flow Forecast",
  scm: "Supply Chain",
  items: "Items",
  inventory: "Inventory",
  purchasing: "Purchasing",
  pr: "Purchase Requisitions",
  rfq: "Request for Quotation",
  po: "Purchase Orders",
  grn: "Goods Receiving",
  warehouse: "Warehouse",
  crm: "CRM",
  leads: "Leads",
  opportunities: "Opportunities",
  customers: "Customers",
  quotations: "Sales Quotations",
  "sales-orders": "Sales Orders",
  "delivery-orders": "Delivery Orders",
  mrp: "MRP",
  bom: "Bill of Materials",
  "work-centers": "Work Centers",
  routings: "Routings",
  production: "Production Planning",
  "work-orders": "Work Orders",
  "quality-control": "Quality Control",
  hrm: "HRM",
  employees: "Employees",
  organization: "Organization",
  attendance: "Attendance",
  leave: "Leave",
  payroll: "Payroll",
  claims: "Claims",
  recruitment: "Recruitment",
  performance: "Performance",
  admin: "Administration",
  users: "Users",
  roles: "Roles & Permissions",
  "menu-access": "Menu Access",
  approvals: "Approvals",
  "numbering-series": "Numbering Series",
  notifications: "Notifications",
  settings: "Settings",
};

function getBreadcrumbs(pathname: string): { label: string; href: string }[] {
  const parts = pathname.split("/").filter(Boolean);
  const crumbs: { label: string; href: string }[] = [];
  let currentPath = "";

  for (const part of parts) {
    if (part === "app") continue;
    currentPath += `/${part}`;
    const label = breadcrumbs[part] || part;
    crumbs.push({ label, href: `/app${currentPath}` });
  }

  return crumbs;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const crumbs = getBreadcrumbs(location.pathname);
  const { data: companies } = useCompanies();
  const [companyOpen, setCompanyOpen] = useState(false);
  const currentCompanyId = localStorage.getItem("current_company_id");
  const currentCompany = companies?.find((c) => c.id === currentCompanyId);

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-secondary-200 bg-white px-4 md:px-6">
      {/* Mobile hamburger */}
      <button
        onClick={onMenuClick}
        className="rounded p-1 text-secondary-500 hover:bg-secondary-100 lg:hidden"
        aria-label="Open menu"
      >
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      {/* Breadcrumb */}
      <nav className="flex-1 overflow-hidden">
        <ol className="flex items-center gap-1 text-sm text-secondary-500">
          {crumbs.map((crumb, index) => (
            <li key={crumb.href} className="flex items-center gap-1">
              {index > 0 && (
                <svg
                  className="h-4 w-4 shrink-0 text-secondary-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              )}
              {index === crumbs.length - 1 ? (
                <span className="font-medium text-secondary-900">{crumb.label}</span>
              ) : (
                <Link to={crumb.href} className="hover:text-secondary-700">
                  {crumb.label}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>

      {/* Company Switcher */}
      <div className="relative hidden md:block">
        <button
          onClick={() => setCompanyOpen(!companyOpen)}
          className="flex items-center gap-1.5 rounded-md border border-secondary-200 px-2.5 py-1.5 text-xs font-medium text-secondary-600 hover:bg-secondary-50"
          aria-label="Switch company"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          <span>{currentCompany?.name || "Select Company"}</span>
          <svg className={`h-3 w-3 transition-transform ${companyOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {companyOpen && companies && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setCompanyOpen(false)} />
            <div className="absolute right-0 top-full z-20 mt-1 w-48 rounded-md border border-secondary-200 bg-white py-1 shadow-lg">
              {companies.length === 0 && (
                <p className="px-3 py-2 text-xs text-secondary-400">No companies</p>
              )}
              {companies.map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    localStorage.setItem("current_company_id", c.id);
                    setCompanyOpen(false);
                    window.location.reload();
                  }}
                  className={`flex w-full items-center px-3 py-2 text-left text-sm hover:bg-secondary-50 ${
                    c.id === currentCompanyId
                      ? "bg-primary-50 font-medium text-primary-700"
                      : "text-secondary-700"
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <button
          className="relative rounded p-1 text-secondary-500 hover:bg-secondary-100"
          aria-label="Notifications"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-500 text-[10px] font-bold text-white">
            3
          </span>
        </button>

        {/* User avatar */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600 text-sm font-medium text-white">
            A
          </div>
          <span className="hidden text-sm font-medium text-secondary-700 md:block">
            Admin
          </span>
        </div>
      </div>
    </header>
  );
}

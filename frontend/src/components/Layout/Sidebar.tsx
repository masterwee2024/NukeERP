import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { useMenu } from "@/hooks/useMenu";
import {
  useCompanies,
  useCurrentCompany,
  useCompanyMutations,
} from "@/hooks/useCompanyContext";
import SidebarGroup from "./SidebarGroup";
import SidebarItem from "./SidebarItem";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { data: menus, isLoading } = useMenu();
  const { data: companies } = useCompanies();
  const { company: currentCompany } = useCurrentCompany();
  const { switchCompany } = useCompanyMutations();
  const [companyOpen, setCompanyOpen] = useState(false);
  const location = useLocation();

  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} />}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-secondary-900 text-white transition-transform duration-300 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between border-b border-secondary-700 px-4">
          <Link to="/app/dashboard" className="text-xl font-bold text-primary-400">
            pyERP
          </Link>
          <button
            onClick={onClose}
            className="rounded p-1 text-secondary-400 hover:bg-secondary-700 hover:text-white"
            aria-label="Close sidebar"
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Company Switcher */}
        <div className="border-b border-secondary-700 px-4 py-3">
          <div className="relative">
            <button
              onClick={() => setCompanyOpen(!companyOpen)}
              className="flex w-full items-center gap-2 rounded-md bg-secondary-800 px-2.5 py-2 text-left text-xs font-medium text-secondary-200 hover:bg-secondary-700"
            >
              <svg
                className="h-3.5 w-3.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                />
              </svg>
              <span className="flex-1 truncate">
                {currentCompany?.name || "Select Company"}
              </span>
              {(companies?.length ?? 0) > 1 && (
                <svg
                  className={`h-3 w-3 shrink-0 transition-transform ${companyOpen ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              )}
            </button>
            {companyOpen && (companies?.length ?? 0) > 1 && (
              <div className="absolute left-0 top-full z-30 mt-1 w-full rounded-md border border-secondary-600 bg-secondary-800 py-1 shadow-lg">
                {companies?.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      localStorage.setItem("current_company_id", c.id);
                      switchCompany.mutate(c.id, {
                        onSettled: () => {
                          setCompanyOpen(false);
                          window.location.reload();
                        },
                      });
                    }}
                    className={`flex w-full items-center px-3 py-2 text-left text-sm ${
                      c.id === currentCompany?.id
                        ? "bg-primary-600/20 font-medium text-primary-300"
                        : "text-secondary-300 hover:bg-secondary-700"
                    }`}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-4">
          {isLoading ? (
            <div className="space-y-2 px-2">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-8 animate-pulse rounded bg-secondary-700" />
              ))}
            </div>
          ) : (
            <ul className="space-y-1">
              {menus?.map((item) =>
                item.children.length > 0 ? (
                  <SidebarGroup
                    key={item.id}
                    item={item}
                    collapsed={false}
                    currentPath={location.pathname}
                  />
                ) : (
                  <SidebarItem
                    key={item.id}
                    item={item}
                    collapsed={false}
                    currentPath={location.pathname}
                  />
                )
              )}
            </ul>
          )}
        </nav>
      </aside>
    </>
  );
}

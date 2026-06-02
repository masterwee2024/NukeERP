import { useLocation, Link } from "react-router-dom";
import { useMenu } from "@/hooks/useMenu";
import SidebarGroup from "./SidebarGroup";
import SidebarItem from "./SidebarItem";

interface SidebarProps {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}

export default function Sidebar({
  open,
  collapsed,
  onClose,
  onToggleCollapse,
}: SidebarProps) {
  const { data: menus, isLoading } = useMenu();
  const location = useLocation();

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:z-30 bg-secondary-900 text-white transition-all duration-300 ${
          collapsed ? "lg:w-16" : "lg:w-60"
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b border-secondary-700 px-4">
          {!collapsed && (
            <Link to="/app/dashboard" className="text-xl font-bold text-primary-400">
              pyERP
            </Link>
          )}
          <button
            onClick={onToggleCollapse}
            className="rounded p-1 text-secondary-400 hover:bg-secondary-700 hover:text-white"
            aria-label="Toggle sidebar"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {collapsed ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 5l7 7-7 7M5 5l7 7-7 7"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Navigation */}
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
                    collapsed={collapsed}
                    currentPath={location.pathname}
                  />
                ) : (
                  <SidebarItem
                    key={item.id}
                    item={item}
                    collapsed={collapsed}
                    currentPath={location.pathname}
                  />
                )
              )}
            </ul>
          )}
        </nav>
      </aside>

      {/* Mobile sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform bg-secondary-900 text-white transition-transform duration-300 lg:hidden ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
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

        {/* Navigation */}
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

import { useState } from "react";
import { Link } from "react-router-dom";
import type { MenuItem } from "@/types/menu";
import SidebarItem from "./SidebarItem";

interface SidebarGroupProps {
  item: MenuItem;
  collapsed: boolean;
  currentPath: string;
}

const iconMap: Record<string, string> = {
  DollarSign:
    "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  Landmark: "M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z",
  PiggyBank:
    "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z",
  Package: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
  Users:
    "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z",
  Factory:
    "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  UserCog:
    "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  Settings:
    "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  GitBranch:
    "M6 3v12m0 0a3 3 0 106 0m-6 0a3 3 0 10-6-3m12-3v6m0 0a3 3 0 106 0m-6 0a3 3 0 10-6-3m-6 0h18",
  Pencil:
    "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z",
  Upload:
    "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4m7-4l4 4m0 0l4-4m-4 4V3",
  Database:
    "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4",
  FileText:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  BarChart3:
    "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
};

function getIcon(iconName: string): string {
  return iconMap[iconName] || "M4 6h16M4 12h16M4 18h16";
}

export default function SidebarGroup({
  item,
  collapsed,
  currentPath,
}: SidebarGroupProps) {
  const [expanded, setExpanded] = useState(() => {
    return item.children.some(
      (child) => currentPath === child.url || currentPath.startsWith(child.url + "/")
    );
  });

  const hasActiveChild = item.children.some(
    (child) => currentPath === child.url || currentPath.startsWith(child.url + "/")
  );

  if (collapsed) {
    return (
      <li>
        <Link
          to={item.children[0]?.url || item.url}
          title={item.name}
          className={`flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors ${
            hasActiveChild
              ? "bg-primary-600 text-white"
              : "text-secondary-300 hover:bg-secondary-700 hover:text-white"
          }`}
        >
          <svg
            className={`h-5 w-5 ${hasActiveChild ? "text-white" : "text-secondary-400"}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d={getIcon(item.icon)}
            />
          </svg>
        </Link>
      </li>
    );
  }

  return (
    <li>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          hasActiveChild
            ? "bg-secondary-700 text-white"
            : "text-secondary-300 hover:bg-secondary-700 hover:text-white"
        }`}
      >
        <svg
          className={`h-5 w-5 shrink-0 ${hasActiveChild ? "text-white" : "text-secondary-400"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d={getIcon(item.icon)}
          />
        </svg>
        <span className="flex-1 text-left">{item.name}</span>
        <svg
          className={`h-4 w-4 shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
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
      </button>
      {expanded && (
        <ul className="ml-4 mt-1 space-y-1 border-l border-secondary-700 pl-2">
          {item.children.map((child) =>
            child.children.length > 0 ? (
              <SidebarGroup
                key={child.id}
                item={child}
                collapsed={false}
                currentPath={currentPath}
              />
            ) : (
              <SidebarItem
                key={child.id}
                item={child}
                collapsed={false}
                currentPath={currentPath}
              />
            )
          )}
        </ul>
      )}
    </li>
  );
}

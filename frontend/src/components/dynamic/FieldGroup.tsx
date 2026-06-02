import { useState, type ReactNode } from "react";

interface FieldGroupProps {
  title: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
  children: ReactNode;
}

export default function FieldGroup({
  title,
  collapsible = true,
  defaultOpen = true,
  children,
}: FieldGroupProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-md border border-secondary-200 bg-white">
      <button
        type="button"
        onClick={() => collapsible && setOpen(!open)}
        className={`flex w-full items-center justify-between px-4 py-3 text-left ${
          collapsible ? "cursor-pointer hover:bg-secondary-50" : "cursor-default"
        }`}
      >
        <h4 className="text-sm font-semibold text-secondary-800">{title}</h4>
        {collapsible && (
          <svg
            className={`h-4 w-4 text-secondary-500 transition-transform ${open ? "rotate-180" : ""}`}
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
      {open && (
        <div className="border-t border-secondary-100 px-4 py-3">{children}</div>
      )}
    </div>
  );
}

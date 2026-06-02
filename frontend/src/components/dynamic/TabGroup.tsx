import { useState, type ReactNode } from "react";

interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

interface TabGroupProps {
  tabs: Tab[];
  activeTab?: string;
  onChange?: (key: string) => void;
}

export default function TabGroup({
  tabs,
  activeTab: controlledTab,
  onChange,
}: TabGroupProps) {
  const [internalTab, setInternalTab] = useState(tabs[0]?.key || "");
  const activeTab = controlledTab ?? internalTab;

  function handleTabClick(key: string) {
    if (onChange) {
      onChange(key);
    } else {
      setInternalTab(key);
    }
  }

  return (
    <div>
      <div className="flex border-b border-secondary-200" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            onClick={() => handleTabClick(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium outline-none transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-primary-600 text-primary-700"
                : "text-secondary-500 hover:text-secondary-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="pt-4">{tabs.find((t) => t.key === activeTab)?.content}</div>
    </div>
  );
}

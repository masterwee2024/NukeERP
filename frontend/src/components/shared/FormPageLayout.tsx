import { useState, useRef, useCallback, useEffect } from "react";

interface PanelDef {
  id: string;
  label: string;
  content: React.ReactNode;
}

interface FormPageLayoutProps {
  leftPanel: PanelDef;
  rightPanel: PanelDef;
}

export default function FormPageLayout({ leftPanel, rightPanel }: FormPageLayoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [splitPercent, setSplitPercent] = useState(30);
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.round((x / rect.width) * 100);
      setSplitPercent(Math.max(20, Math.min(80, pct)));
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    }
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <>
      {/* Desktop: resizable split-pane */}
      <div ref={containerRef} className="hidden xl:flex h-full w-full">
        <div
          className="overflow-auto"
          style={{ flex: `0 0 ${splitPercent}%`, minWidth: 0 }}
        >
          {leftPanel.content}
        </div>
        <div
          onMouseDown={handleMouseDown}
          className={`flex-shrink-0 w-1.5 cursor-col-resize bg-secondary-200 hover:bg-primary-400 active:bg-primary-500 transition-colors ${
            isDragging ? "bg-primary-500" : ""
          }`}
        />
        <div
          className="overflow-auto"
          style={{ flex: `0 0 ${100 - splitPercent}%`, minWidth: 0 }}
        >
          {rightPanel.content}
        </div>
      </div>
      {/* Tablet: stacked */}
      <div className="xl:hidden space-y-4">
        {leftPanel.content}
        {rightPanel.content}
      </div>
    </>
  );
}

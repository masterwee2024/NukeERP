import type { ReactNode } from "react";
import { useViewport } from "@/hooks/useViewport";

interface GridItem {
  colSpan: number;
  children: ReactNode;
  key: string;
}

interface GridLayoutProps {
  items: GridItem[];
  mobileColSpan?: number;
}

const spanClassMap: Record<number, string> = {
  1: "col-span-1",
  2: "col-span-2",
  3: "col-span-3",
  4: "col-span-4",
  5: "col-span-5",
  6: "col-span-6",
  7: "col-span-7",
  8: "col-span-8",
  9: "col-span-9",
  10: "col-span-10",
  11: "col-span-11",
  12: "col-span-12",
};

export default function GridLayout({ items, mobileColSpan = 12 }: GridLayoutProps) {
  const { isMobile } = useViewport();

  return (
    <div className="grid grid-cols-12 gap-4">
      {items.map((item) => {
        const span = Math.min(isMobile ? Math.min(item.colSpan, mobileColSpan) : item.colSpan, 12);
        return (
          <div key={item.key} className={spanClassMap[span] || "col-span-12"}>
            {item.children}
          </div>
        );
      })}
    </div>
  );
}

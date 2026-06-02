import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SidebarItem from "@/components/Layout/SidebarItem";

const mockMenuItem = {
  id: "1",
  name: "Dashboard",
  slug: "dashboard",
  icon: "LayoutDashboard",
  url: "/app/dashboard",
  level: 0,
  module: "core",
  sort_order: 1,
  children: [],
};

describe("SidebarItem", () => {
  it("renders item name", () => {
    render(
      <MemoryRouter>
        <SidebarItem item={mockMenuItem} collapsed={false} currentPath="/" />
      </MemoryRouter>
    );

    expect(screen.getByText("Dashboard")).toBeDefined();
  });

  it("applies active style when current path matches", () => {
    render(
      <MemoryRouter>
        <SidebarItem
          item={mockMenuItem}
          collapsed={false}
          currentPath="/app/dashboard"
        />
      </MemoryRouter>
    );

    const link = screen.getByText("Dashboard").closest("a");
    expect(link?.className).toContain("bg-primary-600");
  });

  it("does not apply active style when path differs", () => {
    render(
      <MemoryRouter>
        <SidebarItem item={mockMenuItem} collapsed={false} currentPath="/app/other" />
      </MemoryRouter>
    );

    const link = screen.getByText("Dashboard").closest("a");
    expect(link?.className).not.toContain("bg-primary-600");
  });

  it("hides text when collapsed", () => {
    render(
      <MemoryRouter>
        <SidebarItem item={mockMenuItem} collapsed={true} currentPath="/" />
      </MemoryRouter>
    );

    expect(screen.queryByText("Dashboard")).toBeNull();
  });

  it("renders icon", () => {
    render(
      <MemoryRouter>
        <SidebarItem item={mockMenuItem} collapsed={false} currentPath="/" />
      </MemoryRouter>
    );

    const svg = screen.getByText("Dashboard").closest("a")?.querySelector("svg");
    expect(svg).toBeDefined();
  });
});

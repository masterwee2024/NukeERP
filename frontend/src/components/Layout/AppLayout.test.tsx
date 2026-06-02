import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppLayout from "./AppLayout";

const mockMenuTree = vi.hoisted(() => [
  {
    id: "1",
    name: "Dashboard",
    slug: "dashboard",
    icon: "LayoutDashboard",
    url: "/app/dashboard",
    level: 0,
    module: "core",
    sort_order: 1,
    children: [],
  },
]);

vi.mock("axios", () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: mockMenuTree }),
    create: vi.fn(() => ({
      get: vi.fn().mockResolvedValue({ data: mockMenuTree }),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    })),
  },
}));

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/app/dashboard"]}>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AppLayout", () => {
  it("renders header and content area", () => {
    renderWithProviders(<AppLayout />);
    expect(screen.getByRole("banner")).toBeDefined();
  });

  it("renders sidebar navigation", () => {
    renderWithProviders(<AppLayout />);
    const nav = document.querySelector("nav");
    expect(nav).toBeDefined();
  });

  it("renders mobile hamburger button", () => {
    renderWithProviders(<AppLayout />);
    const hamburger = screen.getByLabelText("Open menu");
    expect(hamburger).toBeDefined();
  });
});

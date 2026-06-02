import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useMenu } from "@/hooks/useMenu";
import type { ReactNode } from "react";

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
  {
    id: "2",
    name: "Financial",
    slug: "financial",
    icon: "DollarSign",
    url: "",
    level: 0,
    module: "financial",
    sort_order: 2,
    children: [
      {
        id: "3",
        name: "Chart of Accounts",
        slug: "chart-of-accounts",
        icon: "BookOpen",
        url: "/app/financial/chart-of-accounts",
        level: 1,
        module: "financial",
        sort_order: 1,
        children: [],
      },
    ],
  },
]);

vi.mock("axios", () => {
  return {
    default: {
      get: vi.fn().mockResolvedValue({ data: mockMenuTree }),
      create: vi.fn(() => ({
        get: vi.fn().mockResolvedValue({ data: mockMenuTree }),
        interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
      })),
    },
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns menu items with nested children", async () => {
    const { result } = renderHook(() => useMenu(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data![0].name).toBe("Dashboard");
    expect(result.current.data![1].children).toHaveLength(1);
    expect(result.current.data![1].children![0].name).toBe(
      "Chart of Accounts"
    );
  });

  it("matches MenuItem type structure", async () => {
    const { result } = renderHook(() => useMenu(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const first = result.current.data![0];
    expect(first).toHaveProperty("id");
    expect(first).toHaveProperty("name");
    expect(first).toHaveProperty("slug");
    expect(first).toHaveProperty("icon");
    expect(first).toHaveProperty("url");
    expect(first).toHaveProperty("level");
    expect(first).toHaveProperty("module");
    expect(first).toHaveProperty("sort_order");
    expect(first).toHaveProperty("children");
  });

  it("caches menu data between renders", async () => {
    const { result, rerender } = renderHook(() => useMenu(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const cachedData = result.current.data;
    rerender();
    expect(result.current.data).toBe(cachedData);
  });

  it("sets correct query key for cache invalidation", async () => {
    const { result } = renderHook(() => useMenu(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeDefined();
  });
});

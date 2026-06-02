import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const mockPost = vi.fn();

vi.mock("@/lib/api", () => ({
  default: {
    post: mockPost,
    get: vi.fn(),
  },
}));

async function renderHookWithProviders() {
  const { AuthProvider, useAuth } = await import("@/contexts/AuthContext");
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  function TestComponent() {
    const auth = useAuth();
    return (
      <div>
        <span data-testid="status">
          {auth.user ? `User: ${auth.user.email}` : "No user"}
        </span>
        <button onClick={() => auth.login("a@b.com", "pw")}>Login</button>
        <button onClick={() => auth.logout()}>Logout</button>
      </div>
    );
  }

  render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );

  return { useAuth };
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
    mockPost.mockReset();
  });

  it("shows no user when not authenticated", async () => {
    await renderHookWithProviders();
    expect(screen.getByTestId("status").textContent).toBe("No user");
  });

  it("sets user on successful login", async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        access: "test-access-token",
        refresh: "test-refresh-token",
        user: { id: "1", email: "a@b.com" },
      },
    });
    await renderHookWithProviders();
    fireEvent.click(screen.getByText("Login"));
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("User: a@b.com");
    });
  });

  it("clears user on logout", async () => {
    await renderHookWithProviders();
    fireEvent.click(screen.getByText("Logout"));
    await waitFor(() => {
      expect(localStorage.getItem("access_token")).toBeNull();
    });
  });
});

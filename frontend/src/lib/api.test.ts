import { describe, it, expect, vi, beforeEach } from "vitest";

const mockAxios = vi.hoisted(() => {
  const requestUse = vi.fn();
  const responseUse = vi.fn();
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: requestUse },
      response: { use: responseUse },
    },
    defaults: { headers: {} },
  };
  const create = vi.fn(() => mockInstance);
  return {
    mockRequestUse: requestUse,
    mockResponseUse: responseUse,
    mockCreate: create,
  };
});

vi.mock("axios", () => ({
  default: { create: mockAxios.mockCreate },
  create: mockAxios.mockCreate,
}));

describe("API client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetModules();
    mockAxios.mockRequestUse.mockClear();
    mockAxios.mockResponseUse.mockClear();
  });

  it("creates axios instance with /api/v1 base URL", async () => {
    await import("@/lib/api");
    expect(mockAxios.mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ baseURL: "/api/v1" })
    );
  });

  it("exports default api instance", async () => {
    const m = await import("@/lib/api");
    expect(m.default).toBeDefined();
  });

  it("registers request and response interceptors on init", async () => {
    await import("@/lib/api");
    expect(mockAxios.mockRequestUse).toHaveBeenCalledOnce();
    expect(mockAxios.mockResponseUse).toHaveBeenCalledOnce();
  });

  it("fires concurrency-conflict event on 409 response", async () => {
    await import("@/lib/api");

    const handler = vi.fn();
    window.addEventListener("concurrency-conflict", handler);

    const errorHandler = mockAxios.mockResponseUse.mock.calls[0][1];
    const error = {
      response: { status: 409, data: { detail: "Conflict error" } },
      config: {},
    };

    await expect(errorHandler(error)).rejects.toEqual(error);
    expect(handler).toHaveBeenCalledOnce();

    const event = handler.mock.calls[0][0] as CustomEvent;
    expect(event.detail.message).toBe("Conflict error");
  });

  it("includes detail and conflict flag in event data", async () => {
    await import("@/lib/api");

    const handler = vi.fn();
    window.addEventListener("concurrency-conflict", handler);

    const errorHandler = mockAxios.mockResponseUse.mock.calls[0][1];
    const error = {
      response: {
        status: 409,
        data: { detail: "Stale version", conflict: true },
      },
      config: {},
    };

    await expect(errorHandler(error)).rejects.toEqual(error);
    expect(handler).toHaveBeenCalledOnce();

    const event = handler.mock.calls[0][0] as CustomEvent;
    expect(event.detail.message).toBe("Stale version");
    expect(event.detail.data.conflict).toBe(true);
  });

  it("does not fire event for non-409 errors", async () => {
    await import("@/lib/api");

    const handler = vi.fn();
    window.addEventListener("concurrency-conflict", handler);

    const errorHandler = mockAxios.mockResponseUse.mock.calls[0][1];
    const error = {
      response: { status: 400, data: { detail: "Bad request" } },
      config: {},
    };

    await expect(errorHandler(error)).rejects.toEqual(error);
    expect(handler).not.toHaveBeenCalled();
  });

  it("attaches Bearer token when access_token in localStorage", async () => {
    localStorage.setItem("access_token", "my-token");
    await import("@/lib/api");

    const reqHandler = mockAxios.mockRequestUse.mock.calls[0][0];
    const config = { headers: {} };
    const result = reqHandler(config);

    expect(result.headers.Authorization).toBe("Bearer my-token");
  });

  it("omits Authorization header without access_token", async () => {
    await import("@/lib/api");

    const reqHandler = mockAxios.mockRequestUse.mock.calls[0][0];
    const config = { headers: {} };
    const result = reqHandler(config);

    expect(result.headers.Authorization).toBeUndefined();
  });

  it("attaches X-Company-Id header when current_company_id in localStorage", async () => {
    localStorage.setItem("current_company_id", "company-123");
    await import("@/lib/api");

    const reqHandler = mockAxios.mockRequestUse.mock.calls[0][0];
    const config = { headers: {} };
    const result = reqHandler(config);

    expect(result.headers["X-Company-Id"]).toBe("company-123");
  });

  it("omits X-Company-Id header without current_company_id", async () => {
    await import("@/lib/api");

    const reqHandler = mockAxios.mockRequestUse.mock.calls[0][0];
    const config = { headers: {} };
    const result = reqHandler(config);

    expect(result.headers["X-Company-Id"]).toBeUndefined();
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import NotificationBell from "./NotificationBell";

const mockMarkAsRead = vi.fn();
const mockMarkAllAsRead = vi.fn();
const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = (await vi.importActual("react-router-dom")) as any;
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockUseNotifications = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/useNotifications", () => ({
  useNotifications: mockUseNotifications,
}));

function renderWithProviders(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("NotificationBell", () => {
  it("renders badge when unreadCount > 0", () => {
    mockUseNotifications.mockReturnValue({
      notifications: [],
      totalCount: 0,
      unreadCount: 5,
      isLoading: false,
      isWsConnected: true,
      isPushSubscribed: false,
      markAsRead: mockMarkAsRead,
      markAllAsRead: mockMarkAllAsRead,
    });

    renderWithProviders(<NotificationBell />);
    expect(screen.getByText("5")).toBeDefined();
  });

  it("does not render badge when unreadCount is 0", () => {
    mockUseNotifications.mockReturnValue({
      notifications: [],
      totalCount: 0,
      unreadCount: 0,
      isLoading: false,
      isWsConnected: true,
      isPushSubscribed: false,
      markAsRead: mockMarkAsRead,
      markAllAsRead: mockMarkAllAsRead,
    });

    renderWithProviders(<NotificationBell />);
    expect(screen.queryByText("0")).toBeNull();
  });

  it("opens dropdown and lists notifications on click", async () => {
    mockUseNotifications.mockReturnValue({
      notifications: [
        {
          id: "notif-1",
          notification_type: { name: "alert", slug: "alert" },
          title: "New Approval Required",
          message: "Invoice #100 requires approval",
          link: "/app/financial/invoices",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ],
      totalCount: 1,
      unreadCount: 1,
      isLoading: false,
      isWsConnected: true,
      isPushSubscribed: false,
      markAsRead: mockMarkAsRead,
      markAllAsRead: mockMarkAllAsRead,
    });

    renderWithProviders(<NotificationBell />);
    const button = screen.getByLabelText("Notifications, 1 unread");
    fireEvent.click(button);

    expect(screen.getByText("New Approval Required")).toBeDefined();
    expect(screen.getByText("Invoice #100 requires approval")).toBeDefined();
  });

  it("marks notification as read and navigates when clicked", async () => {
    mockUseNotifications.mockReturnValue({
      notifications: [
        {
          id: "notif-1",
          notification_type: { name: "alert", slug: "alert" },
          title: "New Approval Required",
          message: "Invoice #100 requires approval",
          link: "/app/financial/invoices",
          is_read: false,
          created_at: new Date().toISOString(),
        },
      ],
      totalCount: 1,
      unreadCount: 1,
      isLoading: false,
      isWsConnected: true,
      isPushSubscribed: false,
      markAsRead: mockMarkAsRead,
      markAllAsRead: mockMarkAllAsRead,
    });

    renderWithProviders(<NotificationBell />);
    const button = screen.getByLabelText("Notifications, 1 unread");
    fireEvent.click(button);

    const notificationItem = screen.getByText("New Approval Required");
    fireEvent.click(notificationItem);

    expect(mockMarkAsRead).toHaveBeenCalledWith("notif-1");
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/app/financial/invoices");
    });
  });
});

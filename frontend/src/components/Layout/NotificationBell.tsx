import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useNotifications, type Notification } from "@/hooks/useNotifications";

export default function NotificationBell() {
  const navigate = useNavigate();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    isWsConnected,
  } = useNotifications();

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleNotificationClick = async (notif: Notification) => {
    setIsOpen(false);
    if (!notif.is_read) {
      await markAsRead(notif.id);
    }
    if (notif.link) {
      navigate(notif.link);
    }
  };

  const handleViewAll = () => {
    setIsOpen(false);
    navigate("/app/notifications");
  };

  // Format time relative or simple format
  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-full p-1.5 text-secondary-500 transition-colors hover:bg-secondary-100 hover:text-secondary-700 focus:outline-none"
        aria-label={`Notifications, ${unreadCount} unread`}
      >
        <svg
          className={`h-5 w-5 transition-transform duration-300 ${
            isOpen ? "scale-110 text-primary-600" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0.5 right-0.5 flex h-4 w-4 transform items-center justify-center rounded-full bg-danger-500 text-[10px] font-bold text-white transition-all duration-300 scale-100">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}

        {/* WebSocket Connection indicator */}
        <span
          className={`absolute bottom-0 right-0 h-1.5 w-1.5 rounded-full border border-white ${
            isWsConnected ? "bg-success-500" : "bg-warning-500"
          }`}
          title={isWsConnected ? "Real-time connected" : "Connecting to real-time..."}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2.5 z-50 w-80 sm:w-96 rounded-xl border border-secondary-200 bg-white shadow-xl animate-in fade-in slide-in-from-top-3 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-secondary-100 px-4 py-3">
            <h3 className="font-semibold text-secondary-900">Notifications</h3>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllAsRead()}
                className="text-xs font-semibold text-primary-600 hover:text-primary-800 transition-colors"
              >
                Mark all as read
              </button>
            )}
          </div>

          {/* List Container */}
          <div className="max-h-[350px] overflow-y-auto divide-y divide-secondary-100">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
                <svg
                  className="h-10 w-10 text-secondary-300 mb-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-sm font-medium text-secondary-900">All caught up!</p>
                <p className="text-xs text-secondary-500 mt-1">
                  You have no new notifications.
                </p>
              </div>
            ) : (
              notifications.slice(0, 10).map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`flex items-start gap-3 p-4 cursor-pointer transition-colors hover:bg-secondary-50 ${
                    !notif.is_read ? "bg-primary-50/30" : ""
                  }`}
                >
                  {/* Unread indicator dot */}
                  {!notif.is_read && (
                    <div className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary-600" />
                  )}
                  <div className="flex-1">
                    <p className={`text-sm text-secondary-900 ${!notif.is_read ? "font-semibold" : ""}`}>
                      {notif.title}
                    </p>
                    <p className="text-xs text-secondary-600 mt-0.5 line-clamp-2">
                      {notif.message}
                    </p>
                    <span className="text-[10px] text-secondary-400 mt-1.5 block">
                      {formatTime(notif.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-secondary-100 px-4 py-2 text-center">
            <button
              onClick={handleViewAll}
              className="text-xs font-semibold text-primary-600 hover:text-primary-800 transition-colors w-full py-1.5"
            >
              View All Notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState } from "react";
import { useNotifications, type Notification } from "@/hooks/useNotifications";

export default function NotificationCentrePage() {
  const {
    notifications,
    unreadCount,
    isLoading,
    isPushSubscribed,
    markAsRead,
    markAllAsRead,
    subscribePush,
    unsubscribePush,
  } = useNotifications();

  const [filter, setFilter] = useState<"all" | "unread" | "read">("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pushLoading, setPushLoading] = useState(false);
  const itemsPerPage = 10;

  // Filter notifications
  const filteredNotifications = notifications.filter((notif) => {
    if (filter === "unread") return !notif.is_read;
    if (filter === "read") return notif.is_read;
    return true;
  });

  // Paginate notifications
  const totalPages = Math.ceil(filteredNotifications.length / itemsPerPage);
  const paginatedNotifications = filteredNotifications.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const handlePushToggle = async () => {
    setPushLoading(true);
    try {
      if (isPushSubscribed) {
        await unsubscribePush();
      } else {
        await subscribePush();
      }
    } catch (err) {
      console.error(err);
      alert("Failed to update push subscription settings.");
    } finally {
      setPushLoading(false);
    }
  };

  const handleNotificationClick = async (notif: Notification) => {
    if (!notif.is_read) {
      await markAsRead(notif.id);
    }
    if (notif.link) {
      window.location.href = notif.link;
    }
  };

  const formatFullDate = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="md:flex md:items-center md:justify-between mb-8">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-secondary-900 sm:truncate sm:text-3xl">
            Notifications Center
          </h2>
          <p className="mt-1 text-sm text-secondary-500">
            Manage your alerts, reminders, and push subscriptions.
          </p>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0 gap-3">
          {unreadCount > 0 && (
            <button
              onClick={() => markAllAsRead()}
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-secondary-900 shadow-sm ring-1 ring-inset ring-secondary-300 hover:bg-secondary-50 transition-colors duration-150"
            >
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Push Notification Panel */}
        <div className="bg-white rounded-xl border border-secondary-200 p-5 shadow-sm h-fit">
          <h3 className="font-semibold text-secondary-900 mb-3">Push Preferences</h3>
          <p className="text-xs text-secondary-500 mb-4 leading-relaxed">
            Receive real-time notifications on your desktop or mobile device when new actions or
            approvals require your attention.
          </p>
          <div className="flex items-center justify-between border-t border-secondary-100 pt-4">
            <span className="text-sm font-medium text-secondary-700">
              Desktop/Mobile Push
            </span>
            <button
              onClick={handlePushToggle}
              disabled={pushLoading}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-600 focus:ring-offset-2 ${
                isPushSubscribed ? "bg-primary-600" : "bg-secondary-200"
              } ${pushLoading ? "opacity-50 cursor-wait" : ""}`}
              role="switch"
              aria-checked={isPushSubscribed}
            >
              <span
                aria-hidden="true"
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  isPushSubscribed ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Notifications List Panel */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-secondary-200 shadow-sm overflow-hidden flex flex-col">
          {/* Tabs */}
          <div className="border-b border-secondary-200 bg-secondary-50/50 px-4 py-2 flex items-center justify-between shrink-0">
            <div className="flex space-x-1">
              {(["all", "unread", "read"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setFilter(tab);
                    setCurrentPage(1);
                  }}
                  className={`rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition-colors ${
                    filter === tab
                      ? "bg-white text-secondary-900 shadow-sm ring-1 ring-secondary-200"
                      : "text-secondary-500 hover:text-secondary-700"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
            {unreadCount > 0 && (
              <span className="inline-flex items-center rounded-full bg-primary-50 px-2 py-1 text-xs font-medium text-primary-700 ring-1 ring-inset ring-primary-600/10">
                {unreadCount} pending
              </span>
            )}
          </div>

          {/* List content */}
          <div className="divide-y divide-secondary-100 flex-1">
            {isLoading ? (
              <div className="flex justify-center items-center py-20">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              </div>
            ) : paginatedNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
                <svg
                  className="h-12 w-12 text-secondary-300 mb-3"
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
                <h3 className="font-semibold text-secondary-900">No notifications</h3>
                <p className="text-xs text-secondary-500 mt-1 max-w-xs">
                  There are no notifications matching the selected filter.
                </p>
              </div>
            ) : (
              paginatedNotifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`flex items-start gap-4 p-5 transition-colors cursor-pointer hover:bg-secondary-50 ${
                    !notif.is_read ? "bg-primary-50/20" : ""
                  }`}
                >
                  {!notif.is_read && (
                    <div className="mt-2.5 h-2 w-2 shrink-0 rounded-full bg-primary-600" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-sm text-secondary-900 truncate ${!notif.is_read ? "font-semibold" : ""}`}>
                        {notif.title}
                      </p>
                      <span className="text-[10px] text-secondary-400 shrink-0">
                        {formatFullDate(notif.created_at)}
                      </span>
                    </div>
                    <p className="text-xs text-secondary-600 mt-1 leading-relaxed">
                      {notif.message}
                    </p>
                    {notif.link && (
                      <span className="inline-flex items-center text-xs font-semibold text-primary-600 hover:text-primary-800 transition-colors mt-2">
                        View details
                        <svg
                          className="ml-1 h-3 w-3"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2.5}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-secondary-200 bg-secondary-50/30 px-4 py-3 shrink-0">
              <div className="flex flex-1 justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center rounded-md border border-secondary-300 bg-white px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="relative ml-3 inline-flex items-center rounded-md border border-secondary-300 bg-white px-4 py-2 text-sm font-medium text-secondary-700 hover:bg-secondary-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-secondary-700">
                    Showing page <span className="font-semibold">{currentPage}</span> of{" "}
                    <span className="font-semibold">{totalPages}</span>
                  </p>
                </div>
                <div>
                  <nav
                    className="isolate inline-flex -space-x-px rounded-md shadow-sm"
                    aria-label="Pagination"
                  >
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center rounded-l-md px-2 py-2 text-secondary-400 ring-1 ring-inset ring-secondary-300 hover:bg-secondary-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                    >
                      <span className="sr-only">Previous</span>
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fillRule="evenodd"
                          d="M12.79 5.23a.75.75 0 01-.02 1.06L8.83 10l3.94 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        aria-current={currentPage === page ? "page" : undefined}
                        className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold focus:z-20 focus:outline-offset-0 ${
                          currentPage === page
                            ? "z-10 bg-primary-600 text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
                            : "text-secondary-900 ring-1 ring-inset ring-secondary-300 hover:bg-secondary-50 focus:outline-offset-0"
                        }`}
                      >
                        {page}
                      </button>
                    ))}
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center rounded-r-md px-2 py-2 text-secondary-400 ring-1 ring-inset ring-secondary-300 hover:bg-secondary-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                    >
                      <span className="sr-only">Next</span>
                      <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fillRule="evenodd"
                          d="M7.21 14.77a.75.75 0 01.02-1.06L11.17 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

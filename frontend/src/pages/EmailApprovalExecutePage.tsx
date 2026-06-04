import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";

export default function EmailApprovalExecutePage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const action = searchParams.get("action");

  const [status, setStatus] = useState<
    "idle" | "loading" | "success" | "error" | "comment_required"
  >("idle");
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");

  const handleAction = async (commentText = "") => {
    if (!token || !action) {
      setStatus("error");
      setMessage("Invalid URL parameters. Missing token or action.");
      return;
    }

    setStatus("loading");
    try {
      const response = await api.get("/core/approvals/execute", {
        params: {
          token,
          action,
          comment: commentText,
        },
        // Bypass interceptors headers/auth redirects since this is a public link
        headers: {
          Authorization: undefined,
        },
      });
      setStatus("success");
      setMessage(response.data.detail || "Approval processed successfully.");
    } catch (err: any) {
      setStatus("error");
      const errorMsg =
        err.response?.data?.detail || err.message || "Failed to process workflow action.";
      setMessage(errorMsg);
    }
  };

  useEffect(() => {
    if (!token || !action) {
      setStatus("error");
      setMessage("Invalid URL parameters. Missing token or action.");
      return;
    }

    if (action === "reject") {
      setStatus("comment_required");
    } else {
      // Approve immediately
      handleAction();
    }
  }, [token, action]);

  const handleSubmitRejection = (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) {
      alert("Please enter a reason for rejection.");
      return;
    }
    handleAction(comment);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-secondary-200 bg-white p-8 shadow-xl">
        <div className="text-center">
          {/* Logo or App Icon Placeholder */}
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary-100 text-primary-600">
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <h2 className="mt-6 text-2xl font-bold tracking-tight text-secondary-900">
            pyERP Approval Gate
          </h2>
          <p className="mt-2 text-sm text-secondary-500">Secure One-Click Approval System</p>
        </div>

        {status === "loading" && (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
            <p className="mt-4 text-sm font-medium text-secondary-600">
              Processing request, please wait...
            </p>
          </div>
        )}

        {status === "success" && (
          <div className="rounded-xl bg-success-50 p-6 text-center border border-success-200">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-success-100 text-success-600">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h3 className="mt-4 text-base font-semibold text-success-950">Action Completed</h3>
            <p className="mt-2 text-sm text-success-800 leading-relaxed">{message}</p>
            <p className="mt-4 text-xs text-success-600">You can safely close this window now.</p>
          </div>
        )}

        {status === "error" && (
          <div className="rounded-xl bg-danger-50 p-6 text-center border border-danger-200">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-danger-100 text-danger-600">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <h3 className="mt-4 text-base font-semibold text-danger-950">Request Failed</h3>
            <p className="mt-2 text-sm text-danger-800 leading-relaxed">{message}</p>
            <p className="mt-4 text-xs text-danger-600">
              Please contact your administrator if this issue persists.
            </p>
          </div>
        )}

        {status === "comment_required" && (
          <form onSubmit={handleSubmitRejection} className="space-y-6">
            <div className="rounded-md bg-warning-50 p-4 border border-warning-200">
              <div className="flex">
                <div className="shrink-0 text-warning-600">
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.525-1.515 2.525H3.72c-1.345 0-2.188-1.358-1.515-2.525L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-semibold text-warning-950">Rejection Comment</h3>
                  <div className="mt-1 text-xs text-warning-800">
                    You are rejecting this request. Please provide a reason below for the requester.
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label
                htmlFor="comment"
                className="block text-sm font-medium text-secondary-700"
              >
                Reason for Rejection <span className="text-danger-500">*</span>
              </label>
              <div className="mt-2">
                <textarea
                  id="comment"
                  name="comment"
                  rows={4}
                  required
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Explain why you are rejecting this request..."
                  className="block w-full rounded-md border border-secondary-300 px-3 py-2 text-secondary-900 shadow-sm focus:border-primary-600 focus:ring-primary-600 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                className="flex w-full justify-center rounded-md bg-danger-600 px-3 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-danger-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger-600 transition-colors duration-150"
              >
                Confirm Rejection
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

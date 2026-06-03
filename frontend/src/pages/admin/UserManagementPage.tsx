import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import DynamicListDetailPage from "@/components/shared/DynamicListDetailPage";
import api from "@/lib/api";

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const [newPassword, setNewPassword] = useState("");

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/deactivate/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["core/admin/users"] }),
  });
  const reactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/reactivate/`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["core/admin/users"] }),
  });
  const resetPasswordMutation = useMutation({
    mutationFn: async ({ id, password }: { id: string; password: string }) => {
      await api.post(`/core/admin/users/${id}/reset-password/`, {
        new_password: password,
      });
    },
    onSuccess: () => setNewPassword(""),
  });

  return (
    <DynamicListDetailPage
      configKey="admin.users"
      actionSlots={{
        detailHeader: (record, refresh) =>
          (record.is_active as boolean) ? (
            <button
              onClick={async () => {
                const ok = await confirm({
                  title: "Deactivate",
                  message: `Deactivate ${record.email}?`,
                  variant: "danger",
                  confirmText: "Deactivate",
                });
                if (ok) {
                  deactivateMutation.mutate(String(record.id));
                  refresh();
                }
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-danger-600 px-3 py-2 text-sm font-medium text-white hover:bg-danger-700"
            >
              Deactivate
            </button>
          ) : (
            <button
              onClick={async () => {
                const ok = await confirm({
                  title: "Reactivate",
                  message: `Reactivate ${record.email}?`,
                  variant: "warning",
                  confirmText: "Reactivate",
                });
                if (ok) {
                  reactivateMutation.mutate(String(record.id));
                  refresh();
                }
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-success-600 px-3 py-2 text-sm font-medium text-white hover:bg-success-700"
            >
              Reactivate
            </button>
          ),
        detailFooter: (record) => (
          <div className="mt-4 space-y-3 rounded-lg border border-secondary-200 bg-white p-4">
            <h3 className="text-sm font-semibold text-secondary-900">Reset Password</h3>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="New password (min 6 chars)..."
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="flex-1 rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
              <button
                onClick={async () => {
                  if (!newPassword || newPassword.length < 6) return;
                  const ok = await confirm({
                    title: "Reset Password",
                    message: `Reset password for ${record.email}?`,
                    variant: "warning",
                    confirmText: "Reset",
                  });
                  if (ok)
                    resetPasswordMutation.mutate({
                      id: String(record.id),
                      password: newPassword,
                    });
                }}
                className="rounded-lg bg-warning-600 px-4 py-2 text-sm font-medium text-white hover:bg-warning-700 disabled:opacity-50"
              >
                Reset
              </button>
            </div>
          </div>
        ),
      }}
    />
  );
}

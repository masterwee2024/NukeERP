/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

interface Role {
  id: string;
  name: string;
}

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  full_name: string;
  roles: Role[];
}

interface FormState {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  isActive: boolean;
  isStaff: boolean;
  selectedRoleIds: string[];
}

export default function UserFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const isEdit = Boolean(id);

  const [error, setError] = useState("");

  const { data: existingUser } = useQuery({
    queryKey: ["admin-user", id],
    queryFn: async (): Promise<User | null> => {
      const { data } = await api.get("/core/admin/users/");
      const users: User[] = data;
      const found = users.find((u: User) => u.id === id);
      return found ? { ...found } : null;
    },
    enabled: isEdit,
  });

  const [form, setForm] = useState<FormState>({
    email: "",
    password: "",
    firstName: "",
    lastName: "",
    isActive: true,
    isStaff: false,
    selectedRoleIds: [],
  });

  useEffect(() => {
    if (existingUser) {
      setForm({
        email: existingUser.email,
        password: "",
        firstName: existingUser.first_name,
        lastName: existingUser.last_name,
        isActive: existingUser.is_active,
        isStaff: existingUser.is_staff,
        selectedRoleIds: existingUser.roles?.map((r) => r.id) || [],
      });
    }
  }, [existingUser]);

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: async (): Promise<Role[]> => {
      const { data } = await api.get("/core/admin/roles/");
      return data;
    },
  });

  const handleChange = (field: keyof FormState, value: string | boolean | string[]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const createMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const res = await api.post("/core/admin/users/", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      navigate("/app/admin/users");
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || "Failed to create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const res = await api.put(`/core/admin/users/${id}/`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      navigate("/app/admin/users");
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || "Failed to update user");
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async (newPassword: string) => {
      await api.post(`/core/admin/users/${id}/reset-password/`, {
        new_password: newPassword,
      });
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!isEdit) {
      const confirmed = await confirm({
        title: "Create User",
        message: `Create user ${form.email}?`,
        variant: "info",
        confirmLabel: "Create",
      });
      if (!confirmed) return;
      createMutation.mutate({
        email: form.email,
        password: form.password,
        first_name: form.firstName,
        last_name: form.lastName,
        is_active: form.isActive,
        is_staff: form.isStaff,
        role_ids: form.selectedRoleIds,
      });
    } else {
      const confirmed = await confirm({
        title: "Update User",
        message: `Save changes to ${form.email}?`,
        variant: "info",
        confirmLabel: "Save",
      });
      if (!confirmed) return;
      updateMutation.mutate({
        first_name: form.firstName,
        last_name: form.lastName,
        is_active: form.isActive,
        is_staff: form.isStaff,
        role_ids: form.selectedRoleIds,
      });
    }
  };

  const handleResetPassword = async () => {
    const newPassword = prompt("Enter new password:");
    if (!newPassword || newPassword.length < 6) return;
    const confirmed = await confirm({
      title: "Reset Password",
      message: `Reset password for ${form.email}?`,
      variant: "warning",
      confirmLabel: "Reset",
    });
    if (confirmed) {
      resetPasswordMutation.mutate(newPassword);
      alert("Password reset successful");
    }
  };

  const toggleRole = (roleId: string) => {
    setForm((prev) => ({
      ...prev,
      selectedRoleIds: prev.selectedRoleIds.includes(roleId)
        ? prev.selectedRoleIds.filter((id) => id !== roleId)
        : [...prev.selectedRoleIds, roleId],
    }));
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-2xl font-bold text-secondary-900">
        {isEdit ? "Edit User" : "New User"}
      </h1>

      {error && (
        <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-secondary-700">Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => handleChange("email", e.target.value)}
            required
            disabled={isEdit}
            className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none disabled:bg-secondary-100"
          />
        </div>

        {!isEdit && (
          <div>
            <label className="block text-sm font-medium text-secondary-700">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => handleChange("password", e.target.value)}
              required
              minLength={6}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-secondary-700">First Name</label>
            <input
              type="text"
              value={form.firstName}
              onChange={(e) => handleChange("firstName", e.target.value)}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">Last Name</label>
            <input
              type="text"
              value={form.lastName}
              onChange={(e) => handleChange("lastName", e.target.value)}
              className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex gap-6">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.isActive}
              onChange={(e) => handleChange("isActive", e.target.checked)}
              className="rounded border-secondary-300 text-primary-600"
            />
            <span className="text-sm text-secondary-700">Active</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.isStaff}
              onChange={(e) => handleChange("isStaff", e.target.checked)}
              className="rounded border-secondary-300 text-primary-600"
            />
            <span className="text-sm text-secondary-700">Staff (Admin)</span>
          </label>
        </div>

        <div>
          <label className="block text-sm font-medium text-secondary-700">Roles</label>
          <div className="mt-2 flex flex-wrap gap-2">
            {roles?.map((role) => (
              <button
                key={role.id}
                type="button"
                onClick={() => toggleRole(role.id)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  form.selectedRoleIds.includes(role.id)
                    ? "bg-primary-600 text-white"
                    : "bg-secondary-100 text-secondary-600 hover:bg-secondary-200"
                }`}
              >
                {role.name}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-4">
          <div>
            {isEdit && (
              <button
                type="button"
                onClick={handleResetPassword}
                className="text-sm text-warning-600 hover:text-warning-800"
              >
                Reset Password
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate("/app/admin/users")}
              className="rounded-lg border border-secondary-300 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
            >
              {isEdit ? "Save Changes" : "Create User"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

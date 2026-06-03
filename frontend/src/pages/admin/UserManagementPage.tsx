import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, ArrowLeft, Loader2, CheckCircle2, XCircle } from "lucide-react";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";
import { useIsMobile } from "@/hooks/useIsMobile";
import AccordionSection from "@/components/shared/AccordionSection";
import FormPageLayout from "@/components/shared/FormPageLayout";

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
  date_joined: string;
  roles: Role[];
}

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const isMobile = useIsMobile();

  const [viewing, setViewing] = useState<User | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string | null>("basic");
  const [newPassword, setNewPassword] = useState("");

  const [formEmail, setFormEmail] = useState("");
  const [formPassword, setFormPassword] = useState("");
  const [formFirstName, setFormFirstName] = useState("");
  const [formLastName, setFormLastName] = useState("");
  const [formIsActive, setFormIsActive] = useState(true);
  const [formIsStaff, setFormIsStaff] = useState(false);
  const [formSelectedRoleIds, setFormSelectedRoleIds] = useState<string[]>([]);

  const { data: users, isLoading } = useQuery({
    queryKey: ["admin-users", search, roleFilter, statusFilter],
    queryFn: async (): Promise<User[]> => {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (roleFilter) params.set("role_id", roleFilter);
      if (statusFilter) params.set("is_active", statusFilter);
      const { data } = await api.get(`/core/admin/users/?${params.toString()}`);
      return data;
    },
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: async (): Promise<Role[]> => {
      const { data } = await api.get("/core/admin/roles/");
      return data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await api.post("/core/admin/users/", payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      resetForm();
      setShowForm(false);
      setError(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || "Failed to create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: Record<string, unknown> }) => {
      const res = await api.put(`/core/admin/users/${id}/`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setEditing(null);
      setViewing(null);
      setError(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || "Failed to update user");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/deactivate/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setViewing(null);
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/reactivate/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setViewing(null);
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async ({ id, password }: { id: string; password: string }) => {
      await api.post(`/core/admin/users/${id}/reset-password/`, {
        new_password: password,
      });
    },
    onSuccess: () => {
      setNewPassword("");
    },
  });

  const toggleSection = (section: string) => {
    setActiveSection((prev) => (prev === section ? null : section));
  };

  const toggleRole = (roleId: string) => {
    setFormSelectedRoleIds((prev) =>
      prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId]
    );
  };

  const initCreateForm = () => {
    setFormEmail("");
    setFormPassword("");
    setFormFirstName("");
    setFormLastName("");
    setFormIsActive(true);
    setFormIsStaff(false);
    setFormSelectedRoleIds([]);
    setNewPassword("");
    setError(null);
    setActiveSection("basic");
    setShowForm(true);
    setEditing(null);
    setViewing(null);
  };

  const initEditForm = (user: User) => {
    setFormEmail(user.email);
    setFormPassword("");
    setFormFirstName(user.first_name);
    setFormLastName(user.last_name);
    setFormIsActive(user.is_active);
    setFormIsStaff(user.is_staff);
    setFormSelectedRoleIds(user.roles.map((r) => r.id));
    setNewPassword("");
    setError(null);
    setActiveSection("basic");
    setEditing(user);
    setViewing(null);
    setShowForm(false);
  };

  const resetForm = () => {
    setFormEmail("");
    setFormPassword("");
    setFormFirstName("");
    setFormLastName("");
    setFormIsActive(true);
    setFormIsStaff(false);
    setFormSelectedRoleIds([]);
    setNewPassword("");
    setError(null);
  };

  const handleSave = async () => {
    if (editing) {
      const confirmed = await confirm({
        title: "Update User",
        message: `Save changes to ${formEmail}?`,
        variant: "info",
        confirmText: "Save",
      });
      if (!confirmed) return;
      updateMutation.mutate({
        id: editing.id,
        payload: {
          first_name: formFirstName,
          last_name: formLastName,
          is_active: formIsActive,
          is_staff: formIsStaff,
          role_ids: formSelectedRoleIds,
        },
      });
    } else if (showForm) {
      const confirmed = await confirm({
        title: "Create User",
        message: `Create user ${formEmail}?`,
        variant: "warning",
        confirmText: "Create",
      });
      if (!confirmed) return;
      createMutation.mutate({
        email: formEmail,
        password: formPassword,
        first_name: formFirstName,
        last_name: formLastName,
        is_active: formIsActive,
        is_staff: formIsStaff,
        role_ids: formSelectedRoleIds,
      });
    }
  };

  const handleCancel = () => {
    if (editing) {
      setEditing(null);
      setViewing(users?.find((r) => r.id === editing.id) || null);
    } else {
      setShowForm(false);
    }
    setError(null);
  };

  const handleDeactivate = async (user: User) => {
    const confirmed = await confirm({
      title: "Deactivate User",
      message: `Are you sure you want to deactivate ${user.email}? They will not be able to log in.`,
      variant: "danger",
      confirmText: "Deactivate",
    });
    if (confirmed) {
      deactivateMutation.mutate(user.id);
    }
  };

  const handleReactivate = async (user: User) => {
    const confirmed = await confirm({
      title: "Reactivate User",
      message: `Are you sure you want to reactivate ${user.email}?`,
      variant: "warning",
      confirmText: "Reactivate",
    });
    if (confirmed) {
      reactivateMutation.mutate(user.id);
    }
  };

  const handleResetPassword = async () => {
    const target = editing || viewing;
    if (!target || !newPassword || newPassword.length < 6) return;
    const confirmed = await confirm({
      title: "Confirm Reset",
      message: `Reset password for ${target.email}?`,
      variant: "warning",
      confirmText: "Reset",
    });
    if (confirmed) {
      resetPasswordMutation.mutate({ id: target.id, password: newPassword });
    }
  };

  const handleRowClick = (user: User) => {
    setViewing(user);
    setEditing(null);
    setShowForm(false);
    setActiveSection("basic");
    setError(null);
  };

  function renderList() {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-bold text-secondary-900 md:text-xl">Users</h1>
          {!isMobile ? (
            <button
              onClick={initCreateForm}
              className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700"
            >
              <Plus className="h-4 w-4" />+ Add
            </button>
          ) : (
            <button
              onClick={initCreateForm}
              className="flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
            >
              <Plus className="h-5 w-5" />
            </button>
          )}
        </div>

        <div className="mb-4 flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          />
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Roles</option>
            {roles?.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>

        <div className="space-y-2">
          {isLoading ? (
            <div className="py-8 text-center text-secondary-400">
              <Loader2 className="inline h-5 w-5 animate-spin" />
            </div>
          ) : !users || users.length === 0 ? (
            <div className="py-8 text-center text-secondary-400">No users found</div>
          ) : (
            users.map((user) => (
              <div
                key={user.id}
                onClick={() => handleRowClick(user)}
                className="cursor-pointer rounded-lg border border-secondary-200 bg-white p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-secondary-900">
                    {user.full_name || "\u2014"}
                  </span>
                  <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                    user.is_active
                      ? "bg-success-100 text-success-700"
                      : "bg-danger-100 text-danger-700"
                  }`}>
                    {user.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-secondary-500">
                  <span>{user.email}</span>
                  {user.roles.length > 0 && (
                    <span className="flex gap-1">
                      {user.roles.slice(0, 2).map((r) => (
                        <span key={r.id} className="rounded-full bg-primary-100 px-1.5 py-0.5 text-xs text-primary-700">
                          {r.name}
                        </span>
                      ))}
                      {user.roles.length > 2 && (
                        <span className="text-secondary-400">+{user.roles.length - 2}</span>
                      )}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  }

  function renderView(user: User) {
    return (
      <div>
        {error && (
          <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
        )}
        <AccordionSection
          title="Basic Info"
          isOpen={activeSection === "basic"}
          onToggle={() => toggleSection("basic")}
        >
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-secondary-500">Email</span>
              <p className="text-sm text-secondary-900">{user.email}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-secondary-500">Name</span>
              <p className="text-sm text-secondary-900">{user.full_name || "\u2014"}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-secondary-500">Status</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                user.is_active
                  ? "bg-success-100 text-success-700"
                  : "bg-danger-100 text-danger-700"
              }`}>
                {user.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-secondary-500">Staff</span>
              {user.is_staff ? (
                <CheckCircle2 className="h-4 w-4 text-success-600" />
              ) : (
                <XCircle className="h-4 w-4 text-secondary-400" />
              )}
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title="Roles"
          isOpen={activeSection === "roles"}
          onToggle={() => toggleSection("roles")}
        >
          <div className="flex flex-wrap gap-1">
            {user.roles.length === 0 ? (
              <span className="text-sm text-secondary-400">No roles assigned</span>
            ) : (
              user.roles.map((r) => (
                <span key={r.id} className="rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                  {r.name}
                </span>
              ))
            )}
          </div>
        </AccordionSection>

        <div className="mt-6 space-y-4">
          <div className="flex items-center gap-3">
            {!isMobile ? (
              <>
                <button
                  onClick={() => initEditForm(user)}
                  className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
                >
                  Edit
                </button>
                {user.is_active ? (
                  <button
                    onClick={() => handleDeactivate(user)}
                    className="text-sm font-medium text-danger-600 hover:text-danger-800"
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => handleReactivate(user)}
                    className="text-sm font-medium text-success-600 hover:text-success-800"
                  >
                    Reactivate
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  onClick={() => initEditForm(user)}
                  className="flex items-center justify-center rounded-lg bg-primary-600 p-2 text-white hover:bg-primary-700"
                >
                  <Pencil className="h-4 w-4" />
                </button>
                {user.is_active ? (
                  <button
                    onClick={() => handleDeactivate(user)}
                    className="flex items-center justify-center rounded-lg bg-danger-600 p-2 text-white hover:bg-danger-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleReactivate(user)}
                    className="flex items-center justify-center rounded-lg bg-success-600 p-2 text-white hover:bg-success-700"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                  </button>
                )}
              </>
            )}
          </div>

          <div className="space-y-2">
            <input
              type="text"
              placeholder="New password (min 6 chars)..."
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
            />
            <button
              onClick={handleResetPassword}
              disabled={!newPassword || newPassword.length < 6}
              className="text-sm text-warning-600 hover:text-warning-800 disabled:text-secondary-400"
            >
              Reset Password
            </button>
          </div>
        </div>
      </div>
    );
  }

  function renderForm() {
    const isEdit = !!editing;
    const isPending = createMutation.isPending || updateMutation.isPending;

    return (
      <div>
        {error && (
          <div className="mb-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
        )}

        <AccordionSection
          title="Basic Info"
          isOpen={activeSection === "basic"}
          onToggle={() => toggleSection("basic")}
        >
          <div className="space-y-4">
            {!isEdit && (
              <>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">Email</label>
                  <input
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    required
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700">Password</label>
                  <input
                    type="password"
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    required
                    minLength={6}
                    className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                  />
                </div>
              </>
            )}
            {isEdit && (
              <div>
                <label className="block text-sm font-medium text-secondary-700">Email</label>
                <p className="mt-1 text-sm text-secondary-600">{formEmail}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700">First Name</label>
                <input
                  type="text"
                  value={formFirstName}
                  onChange={(e) => setFormFirstName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700">Last Name</label>
                <input
                  type="text"
                  value={formLastName}
                  onChange={(e) => setFormLastName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formIsActive}
                  onChange={(e) => setFormIsActive(e.target.checked)}
                  className="rounded border-secondary-300 text-primary-600"
                />
                <span className="text-sm text-secondary-700">Active</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formIsStaff}
                  onChange={(e) => setFormIsStaff(e.target.checked)}
                  className="rounded border-secondary-300 text-primary-600"
                />
                <span className="text-sm text-secondary-700">Staff (Admin)</span>
              </label>
            </div>
          </div>
        </AccordionSection>

        <AccordionSection
          title="Roles"
          isOpen={activeSection === "roles"}
          onToggle={() => toggleSection("roles")}
        >
          <div className="flex flex-wrap gap-2">
            {roles?.map((role) => (
              <button
                key={role.id}
                type="button"
                onClick={() => toggleRole(role.id)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  formSelectedRoleIds.includes(role.id)
                    ? "bg-primary-600 text-white"
                    : "bg-secondary-100 text-secondary-600 hover:bg-secondary-200"
                }`}
              >
                {role.name}
              </button>
            ))}
          </div>
        </AccordionSection>

        {isEdit && (
          <AccordionSection
            title="Password"
            isOpen={activeSection === "password"}
            onToggle={() => toggleSection("password")}
          >
            <div className="space-y-3">
              <input
                type="text"
                placeholder="New password (min 6 chars)..."
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              />
              <button
                onClick={handleResetPassword}
                disabled={!newPassword || newPassword.length < 6 || resetPasswordMutation.isPending}
                className="text-sm text-warning-600 hover:text-warning-800 disabled:text-secondary-400"
              >
                Reset Password
              </button>
            </div>
          </AccordionSection>
        )}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleCancel}
            className="rounded-lg border border-secondary-300 px-4 py-2 text-sm text-secondary-700 hover:bg-secondary-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isPending}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {isPending ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                {isEdit ? "Saving..." : "Creating..."}
              </span>
            ) : (
              isEdit ? "Save" : "Create"
            )}
          </button>
        </div>
      </div>
    );
  }

  const rightPanelContent = (() => {
    if (editing || showForm) return renderForm();
    if (viewing) return renderView(viewing);
    return (
      <div className="flex items-center justify-center h-full text-secondary-400">
        Select a user to view details
      </div>
    );
  })();

  if (isMobile && (editing || showForm)) {
    return (
      <div className="p-4">
        <button
          onClick={handleCancel}
          className="flex items-center gap-1 text-sm text-secondary-600 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        {renderForm()}
      </div>
    );
  }

  if (isMobile && viewing) {
    return (
      <div className="p-4">
        <button
          onClick={() => setViewing(null)}
          className="flex items-center gap-1 text-sm text-secondary-600 mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        {renderView(viewing)}
      </div>
    );
  }

  if (isMobile) {
    return <div className="p-4">{renderList()}</div>;
  }

  return (
    <FormPageLayout
      leftPanel={{ id: "list", label: "Users", content: renderList() }}
      rightPanel={{ id: "form", label: "Details", content: rightPanelContent }}
    />
  );
}

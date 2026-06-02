import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useConfirm } from "@/components/ui/ConfirmDialog";

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  full_name: string;
  date_joined: string;
  roles: { id: string; name: string }[];
}

interface Role {
  id: string;
  name: string;
}

export default function UserListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { confirm } = useConfirm();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

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

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/deactivate/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/core/admin/users/${userId}/reactivate/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

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

  return (
    <div className="p-4 md:p-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold text-secondary-900 md:text-2xl">Users</h1>
        <button
          onClick={() => navigate("/app/admin/users/new")}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          + New User
        </button>
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

      {/* Mobile: card layout */}
      <div className="space-y-3 md:hidden">
        {isLoading ? (
          <div className="py-8 text-center text-sm text-secondary-400">Loading...</div>
        ) : users?.length === 0 ? (
          <div className="py-8 text-center text-sm text-secondary-400">No users found</div>
        ) : (
          users?.map((user) => (
            <div key={user.id} className="rounded-lg border border-secondary-200 bg-white p-4 shadow-sm">
              <div className="mb-2 flex items-start justify-between">
                <div>
                  <div className="font-medium text-secondary-900">{user.full_name || "—"}</div>
                  <div className="text-sm text-secondary-500">{user.email}</div>
                </div>
                <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                  user.is_active
                    ? "bg-success-100 text-success-700"
                    : "bg-danger-100 text-danger-700"
                }`}>
                  {user.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              {user.roles.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-1">
                  {user.roles.map((r) => (
                    <span key={r.id} className="rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                      {r.name}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex gap-3 border-t border-secondary-100 pt-3 text-sm">
                <button
                  onClick={() => navigate(`/app/admin/users/${user.id}`)}
                  className="font-medium text-primary-600 hover:text-primary-800"
                >
                  Edit
                </button>
                {user.is_active ? (
                  <button
                    onClick={() => handleDeactivate(user)}
                    className="font-medium text-danger-600 hover:text-danger-800"
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => handleReactivate(user)}
                    className="font-medium text-success-600 hover:text-success-800"
                  >
                    Reactivate
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden overflow-x-auto rounded-lg border border-secondary-200 md:block">
        <table className="min-w-full divide-y divide-secondary-200">
          <thead className="bg-secondary-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Email</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Roles</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase text-secondary-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-200">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-secondary-400">Loading...</td>
              </tr>
            ) : users?.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-secondary-400">No users found</td>
              </tr>
            ) : (
              users?.map((user) => (
                <tr key={user.id} className="hover:bg-secondary-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-secondary-900">
                    {user.full_name || "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-secondary-600">{user.email}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-secondary-600">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((r) => (
                        <span key={r.id} className="rounded-full bg-primary-100 px-2 py-0.5 text-xs text-primary-700">
                          {r.name}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      user.is_active
                        ? "bg-success-100 text-success-700"
                        : "bg-danger-100 text-danger-700"
                    }`}>
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => navigate(`/app/admin/users/${user.id}`)}
                        className="text-primary-600 hover:text-primary-800"
                      >
                        Edit
                      </button>
                      {user.is_active ? (
                        <button
                          onClick={() => handleDeactivate(user)}
                          className="text-danger-600 hover:text-danger-800"
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => handleReactivate(user)}
                          className="text-success-600 hover:text-success-800"
                        >
                          Reactivate
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

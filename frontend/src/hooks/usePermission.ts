import { useAuth } from "@/contexts/AuthContext";

export function usePermission() {
  const { user } = useAuth();

  function hasPermission(codename: string): boolean {
    if (!user) return false;
    if (user.is_staff) return true;
    return user.permissions.includes(codename);
  }

  function hasAnyPermission(codenames: string[]): boolean {
    if (!user) return false;
    if (user.is_staff) return true;
    return codenames.some((c) => user.permissions.includes(c));
  }

  function hasRole(roleName: string): boolean {
    if (!user) return false;
    if (user.is_staff) return true;
    return user.roles.some((r) => r.name === roleName);
  }

  return { hasPermission, hasAnyPermission, hasRole };
}

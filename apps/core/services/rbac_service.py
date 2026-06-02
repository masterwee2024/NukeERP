"""RBAC service — role and permission management logic."""

from typing import Any

from apps.core.models import Permission, Role, RolePermission, User, UserRole


def get_user_permissions(user: User) -> list[str]:
    """Return list of permission codenames for a user (via roles)."""
    return list(
        Permission.objects.filter(
            role_permissions__role__user_roles__user=user,
            role_permissions__role__is_active=True,
        )
        .distinct()
        .values_list("codename", flat=True)
    )


def user_has_permission(user: User, codename: str) -> bool:
    """Check if user has a specific permission (superuser has all)."""
    if user.is_superuser:
        return True
    return RolePermission.objects.filter(
        role__user_roles__user=user,
        role__is_active=True,
        permission__codename=codename,
    ).exists()


def user_has_any_permission(user: User, codenames: list[str]) -> bool:
    """Check if user has any of the given permissions."""
    if user.is_superuser:
        return True
    return RolePermission.objects.filter(
        role__user_roles__user=user,
        role__is_active=True,
        permission__codename__in=codenames,
    ).exists()


def get_user_roles(user: User) -> list[Role]:
    """Return list of roles assigned to a user."""
    return list(Role.objects.filter(user_roles__user=user, is_active=True))


def get_role_permissions(role: Role) -> list[Permission]:
    """Return all permissions assigned to a role."""
    return list(
        Permission.objects.filter(role_permissions__role=role).order_by("module", "action")
    )


def assign_role_to_user(user: User, role: Role) -> None:
    """Assign a role to a user."""
    UserRole.objects.get_or_create(user=user, role=role)


def remove_role_from_user(user: User, role: Role) -> None:
    """Remove a role from a user."""
    UserRole.objects.filter(user=user, role=role).delete()


def set_role_permissions(role: Role, permission_ids: list[Any]) -> None:
    """Replace all permissions on a role with the given set."""
    RolePermission.objects.filter(role=role).delete()
    for perm_id in permission_ids:
        try:
            permission = Permission.objects.get(id=perm_id)
            RolePermission.objects.get_or_create(role=role, permission=permission)
        except Permission.DoesNotExist:
            pass


def get_all_permissions_grouped() -> dict[str, list[Permission]]:
    """Return all permissions grouped by module."""
    perms = Permission.objects.all().order_by("module", "action")
    grouped: dict[str, list[Permission]] = {}
    for p in perms:
        grouped.setdefault(p.module, []).append(p)
    return grouped

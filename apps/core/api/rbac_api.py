"""RBAC API — role and permission management endpoints."""

from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import Permission, Role, User, UserRole
from apps.core.services import rbac_service

router = Router()


class PermissionOut(Schema):
    id: str
    module: str
    action: str
    codename: str
    description: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class RoleOut(Schema):
    id: str
    name: str
    description: str = ""
    is_active: bool = True
    is_system: bool = False
    permission_count: int = 0

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_permission_count(obj):
        return obj.role_permissions.count()


class RoleCreate(Schema):
    name: str
    description: str = ""


class RoleUpdate(Schema):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RolePermissionsAssign(Schema):
    permission_ids: list[str]


class UserRoleOut(Schema):
    user_id: str
    role_id: str
    role_name: str


class UserRolesAssign(Schema):
    role_ids: list[str]


# --- Permissions ---


@router.get("/permissions/", response=list[PermissionOut])
def list_permissions(request):
    """List all available permissions."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    return list(Permission.objects.all().order_by("module", "action"))


@router.get("/permissions/grouped/", response=dict)
def list_permissions_grouped(request):
    """List all permissions grouped by module."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    grouped = rbac_service.get_all_permissions_grouped()
    return {
        module: [
            {
                "id": str(p.id),
                "module": p.module,
                "action": p.action,
                "codename": p.codename,
                "description": p.description,
            }
            for p in perms
        ]
        for module, perms in grouped.items()
    }


# --- Roles ---


@router.get("/roles/", response=list[RoleOut])
def list_roles(request):
    """List all roles."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    return list(Role.objects.all().order_by("name"))


@router.post("/roles/", response=RoleOut)
def create_role(request, data: RoleCreate):
    """Create a new role."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    if Role.objects.filter(name=data.name).exists():
        raise HttpError(400, "Role with this name already exists")
    role = Role.objects.create(name=data.name, description=data.description)
    return role


@router.put("/roles/{id}/", response=RoleOut)
def update_role(request, id: UUID, data: RoleUpdate):
    """Update a role."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        role = Role.objects.get(id=id)
    except Role.DoesNotExist:
        raise HttpError(404, "Role not found") from None
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        if Role.objects.filter(name=update_data["name"]).exclude(id=id).exists():
            raise HttpError(400, "Role with this name already exists")
    for field, value in update_data.items():
        role.set_field(field, value)
    role.save()
    return role


@router.delete("/roles/{id}/")
def delete_role(request, id: UUID):
    """Delete a role (system roles cannot be deleted)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        role = Role.objects.get(id=id)
    except Role.DoesNotExist:
        raise HttpError(404, "Role not found") from None
    if role.is_system:
        raise HttpError(400, "System roles cannot be deleted")
    role.delete()
    return {"success": True}


@router.get("/roles/{id}/permissions/", response=list[PermissionOut])
def get_role_permissions(request, id: UUID):
    """Get permissions assigned to a role."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        role = Role.objects.get(id=id)
    except Role.DoesNotExist:
        raise HttpError(404, "Role not found") from None
    return rbac_service.get_role_permissions(role)


@router.put("/roles/{id}/permissions/", response=list[PermissionOut])
def set_role_permissions(request, id: UUID, data: RolePermissionsAssign):
    """Set permissions for a role (replaces all existing)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        role = Role.objects.get(id=id)
    except Role.DoesNotExist:
        raise HttpError(404, "Role not found") from None
    rbac_service.set_role_permissions(role, data.permission_ids)
    return rbac_service.get_role_permissions(role)


# --- User Role Assignment ---


@router.get("/users/{user_id}/roles/", response=list[UserRoleOut])
def get_user_roles(request, user_id: UUID):
    """Get roles assigned to a user."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    return [
        {
            "user_id": str(ur.user_id),
            "role_id": str(ur.role_id),
            "role_name": ur.role.name,
        }
        for ur in UserRole.objects.filter(user=user).select_related("role")
    ]


@router.put("/users/{user_id}/roles/", response=list[UserRoleOut])
def set_user_roles(request, user_id: UUID, data: UserRolesAssign):
    """Set roles for a user (replaces all existing)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    UserRole.objects.filter(user=user).delete()
    roles = Role.objects.filter(id__in=data.role_ids)
    for role in roles:
        UserRole.objects.create(user=user, role=role)
    return get_user_roles(request, user_id)

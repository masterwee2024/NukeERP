"""User management API — admin endpoints for user CRUD."""

from uuid import UUID

from django.db import models
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import LoginHistory, Role, User, UserRole
from apps.core.services import rbac_service

router = Router()


# --- Schemas ---


class UserOut(Schema):
    id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_staff: bool = False
    full_name: str = ""
    date_joined: str = ""
    roles: list[dict] = []

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_full_name(obj):
        return obj.full_name

    @staticmethod
    def resolve_date_joined(obj):
        return obj.date_joined.isoformat() if obj.date_joined else ""

    @staticmethod
    def resolve_roles(obj):
        return [{"id": str(r.id), "name": r.name} for r in rbac_service.get_user_roles(obj)]


class UserCreate(Schema):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_staff: bool = False
    role_ids: list[str] = []


class UserUpdate(Schema):
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None
    role_ids: list[str] | None = None


class UserResetPassword(Schema):
    new_password: str


class LoginHistoryOut(Schema):
    id: str
    ip_address: str | None = None
    user_agent: str = ""
    device_type: str = ""
    is_successful: bool = True
    login_time: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_login_time(obj):
        return obj.login_time.isoformat() if obj.login_time else ""


# --- User CRUD ---


@router.get("/users/", response=list[UserOut])
def list_users(request, search: str = "", role_id: str = "", is_active: str = ""):
    """List users with search and filters (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    qs = User.objects.all().order_by("-date_joined")
    if search:
        qs = qs.filter(
            models.Q(email__icontains=search)
            | models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
        )
    if is_active == "true":
        qs = qs.filter(is_active=True)
    elif is_active == "false":
        qs = qs.filter(is_active=False)
    if role_id:
        qs = qs.filter(user_roles__role_id=role_id)
    return list(qs)


@router.post("/users/", response=UserOut)
def create_user(request, data: UserCreate):
    """Create a new user (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email already registered")
    user = User.objects.create_user(
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        is_active=data.is_active,
        is_staff=data.is_staff,
    )
    if data.role_ids:
        roles = Role.objects.filter(id__in=data.role_ids)
        for role in roles:
            UserRole.objects.create(user=user, role=role)
    return user


@router.put("/users/{id}/", response=UserOut)
def update_user(request, id: UUID, data: UserUpdate):
    """Update a user (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    update_data = data.model_dump(exclude_unset=True)
    role_ids = update_data.pop("role_ids", None)
    for field, value in update_data.items():
        setattr(user, field, value)
    user.save()
    if role_ids is not None:
        UserRole.objects.filter(user=user).delete()
        roles = Role.objects.filter(id__in=role_ids)
        for role in roles:
            UserRole.objects.create(user=user, role=role)
    return user


@router.post("/users/{id}/deactivate/")
def deactivate_user(request, id: UUID):
    """Deactivate a user (soft delete, superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    if user == request.auth:
        raise HttpError(400, "Cannot deactivate yourself")
    user.is_active = False
    user.save()
    return {"success": True}


@router.post("/users/{id}/reactivate/")
def reactivate_user(request, id: UUID):
    """Reactivate a deactivated user (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    user.is_active = True
    user.save()
    return {"success": True}


@router.post("/users/{id}/reset-password/")
def reset_user_password(request, id: UUID, data: UserResetPassword):
    """Admin-initiated password reset (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    user.set_password(data.new_password)
    user.save()
    return {"detail": "Password reset successfully"}


@router.get("/users/{id}/login-history/", response=list[LoginHistoryOut])
def get_login_history(request, id: UUID):
    """Get login history for a user (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        user = User.objects.get(id=id)
    except User.DoesNotExist:
        raise HttpError(404, "User not found") from None
    return list(LoginHistory.objects.filter(user=user)[:50])

"""Authentication API endpoints using Django Ninja."""

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from ninja import Router, Schema
from ninja.errors import HttpError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import User
from apps.core.services import company_service

router = Router()


# --- Schemas ---


class LoginSchema(Schema):
    email: str
    password: str


class RegisterSchema(Schema):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class ForgotPasswordSchema(Schema):
    email: str


class ResetPasswordSchema(Schema):
    uid: str
    token: str
    new_password: str


# --- Public Endpoints (no auth required) ---


def _user_response(user):
    """Build user dict with company info."""
    companies = company_service.get_user_companies(user)
    current = company_service.get_user_default_company(user)
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "full_name": user.full_name,
        "current_company": (
            {
                "id": str(current.id),
                "name": current.name,
                "code": current.code,
            }
            if current
            else None
        ),
        "companies": [
            {"id": str(c.id), "name": c.name, "code": c.code} for c in companies
        ],
    }


@router.post("/login/", auth=None)
def login(request, payload: LoginSchema):
    """Authenticate user and return JWT tokens."""
    user = authenticate(email=payload.email, password=payload.password)

    if user is None:
        raise HttpError(401, "Invalid email or password")

    if not user.is_active:
        raise HttpError(403, "Account is deactivated")

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_response(user),
    }


@router.post("/register/", auth=None)
def register(request, payload: RegisterSchema):
    """Create a new user account."""
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email already registered")

    user = User.objects.create_user(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )

    refresh = RefreshToken.for_user(user)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": _user_response(user),
    }


@router.post("/forgot-password/", auth=None)
def forgot_password(request, payload: ForgotPasswordSchema):
    """Send password reset email."""
    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        return {"detail": "If the email exists, a reset link has been sent"}

    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    return {
        "detail": "If the email exists, a reset link has been sent",
        "reset_token": token,
        "uid": uid,
    }


@router.post("/reset-password/", auth=None)
def reset_password(request, payload: ResetPasswordSchema):
    """Reset password using token."""
    try:
        uid = force_str(urlsafe_base64_decode(payload.uid))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise HttpError(400, "Invalid reset link") from None

    if not default_token_generator.check_token(user, payload.token):
        raise HttpError(400, "Invalid or expired reset token")

    user.set_password(payload.new_password)
    user.save()

    return {"detail": "Password reset successfully"}


# --- Authenticated Endpoints ---


@router.post("/logout/")
def logout(request):
    """Logout (client-side token deletion)."""
    return {"detail": "Logged out successfully"}


@router.get("/me/")
def get_me(request):
    """Get current user profile."""
    return _user_response(request.auth)

"""JWT authentication backend for Django Ninja."""

from django.contrib.auth import get_user_model
from ninja.security import HttpBearer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class JWTAuth(HttpBearer):
    """Validates JWT Bearer tokens for Ninja API endpoints."""

    def authenticate(self, request, token: str):
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            user = User.objects.get(id=user_id)
            return user
        except (TokenError, User.DoesNotExist, KeyError):
            return None

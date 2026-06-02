"""Permission decorator for Django Ninja views."""

from functools import wraps

from ninja.errors import HttpError


def permission_required(codename: str):
    """Decorator that checks if the authenticated user has the given permission.

    Usage:
        @router.get("/items/")
        @permission_required("scm_view")
        def list_items(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.auth
            if user and user.is_authenticated:
                if user.is_superuser:
                    return view_func(request, *args, **kwargs)
                from apps.core.services.rbac_service import user_has_permission

                if user_has_permission(user, codename):
                    return view_func(request, *args, **kwargs)
            raise HttpError(403, "You do not have permission to perform this action")

        return wrapper

    return decorator

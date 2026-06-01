"""Custom exception handler for Django REST Framework."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Unified error response format."""
    response = exception_handler(exc, context)

    if response is not None:
        data = {
            "success": False,
            "errors": response.data,
            "status_code": response.status_code,
        }
        response.data = data
    else:
        # Unhandled exceptions
        data = {
            "success": False,
            "errors": {"detail": str(exc)},
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        response = Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response

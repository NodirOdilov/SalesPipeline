"""
Custom exception handling for the SalesPipeline API.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "success": False,
            "error": {
                "status_code": response.status_code,
                "message": _get_error_message(response),
                "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
            },
        }
        response.data = error_payload
        return response

    # Handle Django native exceptions not caught by DRF
    if isinstance(exc, ValidationError):
        data = {
            "success": False,
            "error": {
                "status_code": 400,
                "message": "Validation error",
                "details": exc.message_dict if hasattr(exc, "message_dict") else {"detail": str(exc)},
            },
        }
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, Http404):
        data = {
            "success": False,
            "error": {
                "status_code": 404,
                "message": "Resource not found",
                "details": {"detail": str(exc)},
            },
        }
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, PermissionDenied):
        data = {
            "success": False,
            "error": {
                "status_code": 403,
                "message": "Permission denied",
                "details": {"detail": str(exc)},
            },
        }
        return Response(data, status=status.HTTP_403_FORBIDDEN)

    # Log unhandled exceptions
    logger.exception(f"Unhandled exception: {exc}", exc_info=exc)

    data = {
        "success": False,
        "error": {
            "status_code": 500,
            "message": "An unexpected error occurred",
            "details": {},
        },
    }
    return Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_error_message(response):
    """Extract a human-readable error message from the response."""
    if isinstance(response.data, dict):
        if "detail" in response.data:
            return str(response.data["detail"])
        if "non_field_errors" in response.data:
            errors = response.data["non_field_errors"]
            return str(errors[0]) if errors else "Validation error"
    if isinstance(response.data, list) and response.data:
        return str(response.data[0])
    return _status_code_to_message(response.status_code)


def _status_code_to_message(code):
    """Map status codes to default messages."""
    messages = {
        400: "Bad request",
        401: "Authentication credentials were not provided or are invalid",
        403: "You do not have permission to perform this action",
        404: "Resource not found",
        405: "Method not allowed",
        409: "Conflict",
        429: "Too many requests",
        500: "Internal server error",
    }
    return messages.get(code, "An error occurred")


class BusinessLogicError(APIException):
    """Exception for business logic violations."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "A business rule was violated."
    default_code = "business_logic_error"


class ResourceConflictError(APIException):
    """Exception for resource conflicts."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested operation conflicts with the current state."
    default_code = "resource_conflict"

"""
Custom permissions for the SalesPipeline API.
"""

from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """Allow access only to admin users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsManager(BasePermission):
    """Allow access to admins and managers."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.MANAGER)
        )


class IsManagerOrOwner(BasePermission):
    """Allow access to admins, managers, or the resource owner."""

    def has_object_permission(self, request, view, obj):
        if request.user.role in (User.Role.ADMIN, User.Role.MANAGER):
            return True
        # Check if the object has a user field or an owner/assigned_to field
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        if hasattr(obj, "assigned_to"):
            return obj.assigned_to == request.user
        return False


class IsSalesRepOrAbove(BasePermission):
    """Allow access to sales reps, managers, and admins (not viewers)."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role != User.Role.VIEWER
        )


class IsTeamMember(BasePermission):
    """Allow access only to members of the same team."""

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return True

        user_team = getattr(
            getattr(request.user, "sales_profile", None), "team_id", None
        )
        if user_team is None:
            return False

        if hasattr(obj, "team_id"):
            return obj.team_id == user_team

        if hasattr(obj, "assigned_to"):
            assigned_team = getattr(
                getattr(obj.assigned_to, "sales_profile", None), "team_id", None
            )
            return assigned_team == user_team

        return False


class ReadOnly(BasePermission):
    """Allow read-only access."""

    def has_permission(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS")

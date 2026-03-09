"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import SalesRep, SalesTeam, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "avatar", "timezone")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "role"),
            },
        ),
    )


@admin.register(SalesTeam)
class SalesTeamAdmin(admin.ModelAdmin):
    list_display = ("name", "manager", "member_count", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    raw_id_fields = ("manager",)


@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    list_display = ("user", "team", "title", "quota", "quota_period", "is_active")
    list_filter = ("team", "is_active", "quota_period")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("user",)

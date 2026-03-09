"""
Admin configuration for leads app.
"""

from django.contrib import admin

from .models import Lead, LeadActivity, LeadScore, LeadSource


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "company",
        "status",
        "priority",
        "assigned_to",
        "current_score",
        "created_at",
    )
    list_filter = ("status", "priority", "source", "created_at")
    search_fields = ("first_name", "last_name", "email", "company")
    raw_id_fields = ("assigned_to", "created_by", "source")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(LeadScore)
class LeadScoreAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "total_score",
        "demographic_score",
        "behavioral_score",
        "engagement_score",
        "firmographic_score",
        "calculated_at",
    )
    list_filter = ("calculated_at",)
    raw_id_fields = ("lead",)


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ("lead", "activity_type", "title", "performed_by", "created_at")
    list_filter = ("activity_type", "created_at")
    search_fields = ("title", "description")
    raw_id_fields = ("lead", "performed_by")

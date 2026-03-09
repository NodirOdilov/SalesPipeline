"""
Admin configuration for pipeline app.
"""

from django.contrib import admin

from .models import Deal, DealHistory, Pipeline, Stage


class StageInline(admin.TabularInline):
    model = Stage
    extra = 1
    ordering = ["order"]


@admin.register(Pipeline)
class PipelineAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "is_active", "deal_count", "total_value", "created_at")
    list_filter = ("is_active", "is_default")
    search_fields = ("name",)
    inlines = [StageInline]


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ("name", "pipeline", "order", "probability", "deal_count", "is_active")
    list_filter = ("pipeline", "is_active")
    ordering = ("pipeline", "order")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "pipeline",
        "stage",
        "value",
        "status",
        "priority",
        "assigned_to",
        "expected_close_date",
        "created_at",
    )
    list_filter = ("pipeline", "stage", "status", "priority", "created_at")
    search_fields = ("title", "contact_name", "company")
    raw_id_fields = ("assigned_to", "created_by", "lead")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")


@admin.register(DealHistory)
class DealHistoryAdmin(admin.ModelAdmin):
    list_display = ("deal", "field_changed", "old_value", "new_value", "changed_by", "changed_at")
    list_filter = ("field_changed", "changed_at")
    raw_id_fields = ("deal", "changed_by")

"""
Serializers for report models.
"""

from rest_framework import serializers

from .models import DashboardWidget, ReportSchedule, SavedReport


class SavedReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing saved reports."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )
    schedule_count = serializers.SerializerMethodField()

    class Meta:
        model = SavedReport
        fields = [
            "id",
            "name",
            "description",
            "report_type",
            "report_type_display",
            "output_format",
            "is_public",
            "last_run_at",
            "schedule_count",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def get_schedule_count(self, obj):
        return obj.schedules.filter(is_active=True).count()


class SavedReportDetailSerializer(serializers.ModelSerializer):
    """Full serializer for saved report detail view."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )
    schedules = serializers.SerializerMethodField()

    class Meta:
        model = SavedReport
        fields = [
            "id",
            "name",
            "description",
            "report_type",
            "report_type_display",
            "output_format",
            "filters",
            "columns",
            "chart_config",
            "is_public",
            "shared_with",
            "last_run_at",
            "cached_result",
            "schedules",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_schedules(self, obj):
        schedules = obj.schedules.filter(is_active=True)
        return ReportScheduleSerializer(schedules, many=True).data


class SavedReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a saved report."""

    class Meta:
        model = SavedReport
        fields = [
            "name",
            "description",
            "report_type",
            "output_format",
            "filters",
            "columns",
            "chart_config",
            "is_public",
            "shared_with",
        ]

    def create(self, validated_data):
        shared_with = validated_data.pop("shared_with", [])
        validated_data["created_by"] = self.context["request"].user
        report = SavedReport.objects.create(**validated_data)
        if shared_with:
            report.shared_with.set(shared_with)
        return report


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ReportSchedule model."""

    report_name = serializers.CharField(source="report.name", read_only=True)
    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )

    class Meta:
        model = ReportSchedule
        fields = [
            "id",
            "report",
            "report_name",
            "frequency",
            "frequency_display",
            "day_of_week",
            "day_of_month",
            "time_of_day",
            "recipients",
            "is_active",
            "last_sent_at",
            "next_run_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "last_sent_at", "created_at", "updated_at"]

    def validate(self, attrs):
        frequency = attrs.get("frequency", "")
        if frequency == "weekly" and attrs.get("day_of_week") is None:
            raise serializers.ValidationError(
                {"day_of_week": "Required for weekly schedules."}
            )
        if frequency == "monthly" and attrs.get("day_of_month") is None:
            raise serializers.ValidationError(
                {"day_of_month": "Required for monthly schedules."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer for DashboardWidget model."""

    widget_type_display = serializers.CharField(
        source="get_widget_type_display", read_only=True
    )

    class Meta:
        model = DashboardWidget
        fields = [
            "id",
            "user",
            "title",
            "widget_type",
            "widget_type_display",
            "data_source",
            "config",
            "grid_x",
            "grid_y",
            "grid_w",
            "grid_h",
            "is_visible",
            "refresh_interval",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class DashboardLayoutSerializer(serializers.Serializer):
    """Serializer for bulk-updating widget positions."""

    widgets = serializers.ListField(
        child=serializers.DictField(), min_length=1
    )

    def validate_widgets(self, value):
        required_keys = {"id", "grid_x", "grid_y", "grid_w", "grid_h"}
        for widget in value:
            if not required_keys.issubset(widget.keys()):
                raise serializers.ValidationError(
                    f"Each widget must include: {required_keys}"
                )
        return value

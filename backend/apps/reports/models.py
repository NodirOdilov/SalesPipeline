"""
Report models: SavedReport, ReportSchedule, DashboardWidget.
"""

import uuid

from django.conf import settings
from django.db import models


class SavedReport(models.Model):
    """Persisted report configuration that can be re-run or scheduled."""

    class ReportType(models.TextChoices):
        PIPELINE = "pipeline", "Pipeline Summary"
        REVENUE = "revenue", "Revenue Analysis"
        CONVERSION = "conversion", "Conversion Rates"
        ACTIVITY = "activity", "Activity Report"
        FORECAST_VS_ACTUAL = "forecast_vs_actual", "Forecast vs Actual"
        LEAD_SOURCE = "lead_source", "Lead Source Analysis"
        REP_PERFORMANCE = "rep_performance", "Rep Performance"
        PRODUCT_MIX = "product_mix", "Product Mix"
        QUOTATION = "quotation", "Quotation Analysis"
        CUSTOM = "custom", "Custom Report"

    class OutputFormat(models.TextChoices):
        JSON = "json", "JSON"
        CSV = "csv", "CSV"
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "Excel"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(
        max_length=30, choices=ReportType.choices, default=ReportType.PIPELINE
    )
    output_format = models.CharField(
        max_length=10, choices=OutputFormat.choices, default=OutputFormat.JSON
    )

    # Filter configuration
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stored filter parameters: date range, pipeline, team, etc.",
    )
    columns = models.JSONField(
        default=list,
        blank=True,
        help_text="Column definitions for tabular reports.",
    )
    chart_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Chart configuration: type, axes, colors, etc.",
    )

    # Sharing
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="shared_reports"
    )

    # Caching
    last_run_at = models.DateTimeField(null=True, blank=True)
    cached_result = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_reports"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportSchedule(models.Model):
    """Schedule for automatic report generation and delivery."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Bi-weekly"
        MONTHLY = "monthly", "Monthly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        SavedReport, on_delete=models.CASCADE, related_name="schedules"
    )
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY
    )
    day_of_week = models.IntegerField(
        null=True,
        blank=True,
        help_text="0=Monday, 6=Sunday. Used for weekly/bi-weekly schedules.",
    )
    day_of_month = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of the month (1-28). Used for monthly schedules.",
    )
    time_of_day = models.TimeField(
        help_text="Time to generate the report (UTC)."
    )
    recipients = models.JSONField(
        default=list,
        help_text="List of email addresses to receive the report.",
    )
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_schedules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_schedules"
        ordering = ["next_run_at"]

    def __str__(self):
        return f"{self.report.name} - {self.get_frequency_display()}"


class DashboardWidget(models.Model):
    """Configurable dashboard widget tied to a user."""

    class WidgetType(models.TextChoices):
        KPI_CARD = "kpi_card", "KPI Card"
        BAR_CHART = "bar_chart", "Bar Chart"
        LINE_CHART = "line_chart", "Line Chart"
        PIE_CHART = "pie_chart", "Pie Chart"
        FUNNEL = "funnel", "Funnel Chart"
        TABLE = "table", "Data Table"
        LEADERBOARD = "leaderboard", "Leaderboard"
        ACTIVITY_FEED = "activity_feed", "Activity Feed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_widgets",
    )
    title = models.CharField(max_length=200)
    widget_type = models.CharField(
        max_length=20, choices=WidgetType.choices, default=WidgetType.KPI_CARD
    )
    data_source = models.CharField(
        max_length=50,
        help_text="API endpoint or report type used to populate the widget.",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Widget-specific configuration: colors, filters, time range, etc.",
    )

    # Layout
    grid_x = models.IntegerField(default=0)
    grid_y = models.IntegerField(default=0)
    grid_w = models.IntegerField(default=4)
    grid_h = models.IntegerField(default=3)

    is_visible = models.BooleanField(default=True)
    refresh_interval = models.IntegerField(
        default=300,
        help_text="Auto-refresh interval in seconds (0 to disable).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_widgets"
        ordering = ["grid_y", "grid_x"]

    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"

"""
Forecasting models: Forecast, ForecastPeriod.
"""

import uuid

from django.conf import settings
from django.db import models


class Forecast(models.Model):
    """Sales forecast for a specific period and scope."""

    class ForecastType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        YEARLY = "yearly", "Yearly"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        FINAL = "final", "Final"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    forecast_type = models.CharField(
        max_length=20, choices=ForecastType.choices, default=ForecastType.MONTHLY
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Scope
    pipeline = models.ForeignKey(
        "pipeline.Pipeline",
        on_delete=models.CASCADE,
        related_name="forecasts",
        null=True,
        blank=True,
    )
    team = models.ForeignKey(
        "accounts.SalesTeam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forecasts",
    )
    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forecasts",
    )

    # Time range
    start_date = models.DateField()
    end_date = models.DateField()

    # Forecast values
    predicted_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    best_case = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    worst_case = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    weighted_pipeline = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    committed = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Actual (filled in after period ends)
    actual_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, null=True, blank=True
    )

    # Metadata
    assumptions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    calculation_details = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_forecasts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "forecasts"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    @property
    def accuracy(self):
        """Calculate forecast accuracy if actual revenue is available."""
        if self.actual_revenue and self.predicted_revenue:
            error = abs(float(self.actual_revenue) - float(self.predicted_revenue))
            return round(
                (1 - error / max(float(self.actual_revenue), 0.01)) * 100, 2
            )
        return None


class ForecastPeriod(models.Model):
    """Breakdown of a forecast by sub-period (e.g., weekly within a monthly forecast)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    forecast = models.ForeignKey(
        Forecast, on_delete=models.CASCADE, related_name="periods"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    label = models.CharField(max_length=100)

    predicted_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actual_revenue = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, null=True, blank=True
    )

    deal_count = models.IntegerField(default=0)
    weighted_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forecast_periods"
        ordering = ["period_start"]

    def __str__(self):
        return f"{self.forecast.name} - {self.label}"

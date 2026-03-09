"""
Pipeline models: Pipeline, Stage, Deal, DealHistory.
"""

import uuid

from django.conf import settings
from django.db import models


class Pipeline(models.Model):
    """Sales pipeline definition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_pipelines",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pipelines"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure only one default pipeline
        if self.is_default:
            Pipeline.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    @property
    def total_value(self):
        return (
            self.deals.filter(status="open").aggregate(total=models.Sum("value"))[
                "total"
            ]
            or 0
        )

    @property
    def deal_count(self):
        return self.deals.filter(status="open").count()


class Stage(models.Model):
    """Stage within a pipeline."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="stages"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    probability = models.IntegerField(
        default=0,
        help_text="Win probability percentage (0-100) for deals in this stage.",
    )
    color = models.CharField(max_length=7, default="#6366f1")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pipeline_stages"
        ordering = ["order"]
        unique_together = ["pipeline", "order"]

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"

    @property
    def deal_count(self):
        return self.deals.filter(status="open").count()

    @property
    def total_value(self):
        return (
            self.deals.filter(status="open").aggregate(total=models.Sum("value"))[
                "total"
            ]
            or 0
        )


class Deal(models.Model):
    """Deal in the sales pipeline."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")

    pipeline = models.ForeignKey(
        Pipeline, on_delete=models.CASCADE, related_name="deals"
    )
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="deals")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )

    # Relationships
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_deals",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_deals",
    )

    # Contact info
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    company = models.CharField(max_length=200, blank=True)

    # Dates
    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    loss_reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "deals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["stage"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["expected_close_date"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.value} {self.currency}"

    @property
    def weighted_value(self):
        """Deal value weighted by stage probability."""
        return float(self.value) * (self.stage.probability / 100)

    @property
    def days_in_pipeline(self):
        from django.utils import timezone

        return (timezone.now().date() - self.created_at.date()).days

    @property
    def days_in_stage(self):
        last_move = self.history.filter(field_changed="stage").order_by("-changed_at").first()
        if last_move:
            from django.utils import timezone
            return (timezone.now().date() - last_move.changed_at.date()).days
        return self.days_in_pipeline


class DealHistory(models.Model):
    """Audit trail for deal changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="history")
    field_changed = models.CharField(max_length=50)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "deal_history"
        ordering = ["-changed_at"]
        verbose_name_plural = "Deal histories"

    def __str__(self):
        return f"{self.deal.title}: {self.field_changed} changed"

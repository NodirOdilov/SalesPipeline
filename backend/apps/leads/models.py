"""
Lead models: Lead, LeadSource, LeadScore, LeadActivity.
"""

import uuid

from django.conf import settings
from django.db import models


class LeadSource(models.Model):
    """Source channel for lead acquisition."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lead_sources"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Lead(models.Model):
    """Lead/prospect in the sales pipeline."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        UNQUALIFIED = "unqualified", "Unqualified"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    source = models.ForeignKey(
        LeadSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_leads",
    )

    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_follow_up = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leads"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.company})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def current_score(self):
        score = self.scores.order_by("-calculated_at").first()
        return score.total_score if score else 0


class LeadScore(models.Model):
    """Computed score for a lead based on various signals."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="scores")

    # Score breakdown
    demographic_score = models.IntegerField(default=0)
    behavioral_score = models.IntegerField(default=0)
    engagement_score = models.IntegerField(default=0)
    firmographic_score = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)

    # Score metadata
    score_details = models.JSONField(default=dict, blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lead_scores"
        ordering = ["-calculated_at"]

    def __str__(self):
        return f"{self.lead.full_name}: {self.total_score}"


class LeadActivity(models.Model):
    """Activity log for a lead."""

    class ActivityType(models.TextChoices):
        NOTE = "note", "Note"
        EMAIL_SENT = "email_sent", "Email Sent"
        EMAIL_OPENED = "email_opened", "Email Opened"
        EMAIL_REPLIED = "email_replied", "Email Replied"
        CALL = "call", "Phone Call"
        MEETING = "meeting", "Meeting"
        TASK = "task", "Task"
        STATUS_CHANGE = "status_change", "Status Change"
        SCORE_UPDATE = "score_update", "Score Update"
        WEBSITE_VISIT = "website_visit", "Website Visit"
        FORM_SUBMISSION = "form_submission", "Form Submission"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lead_activities"
        ordering = ["-created_at"]
        verbose_name_plural = "Lead activities"

    def __str__(self):
        return f"{self.activity_type}: {self.title}"

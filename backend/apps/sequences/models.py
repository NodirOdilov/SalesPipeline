"""
Sequence models: EmailSequence, SequenceStep, SequenceEnrollment.
"""

import uuid

from django.conf import settings
from django.db import models


class EmailSequence(models.Model):
    """Multi-step email sequence definition."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Settings
    send_as = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sequences_as_sender",
        help_text="User whose email credentials will be used to send.",
    )
    reply_to_email = models.EmailField(blank=True)
    track_opens = models.BooleanField(default=True)
    track_clicks = models.BooleanField(default=True)
    stop_on_reply = models.BooleanField(
        default=True,
        help_text="Automatically stop sequence when lead replies.",
    )

    # Metadata
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_sequences",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "email_sequences"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return self.steps.count()

    @property
    def active_enrollments(self):
        return self.enrollments.filter(status="active").count()

    @property
    def total_enrollments(self):
        return self.enrollments.count()


class SequenceStep(models.Model):
    """Individual step in an email sequence."""

    class StepType(models.TextChoices):
        EMAIL = "email", "Email"
        WAIT = "wait", "Wait"
        TASK = "task", "Task"
        CONDITION = "condition", "Condition"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(
        EmailSequence, on_delete=models.CASCADE, related_name="steps"
    )
    order = models.IntegerField(default=0)
    step_type = models.CharField(
        max_length=20, choices=StepType.choices, default=StepType.EMAIL
    )

    # Email content (for email steps)
    subject = models.CharField(max_length=200, blank=True)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)

    # Timing
    delay_days = models.IntegerField(
        default=1,
        help_text="Number of days to wait before executing this step.",
    )
    delay_hours = models.IntegerField(default=0)
    send_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Preferred send time (in lead's timezone if available).",
    )

    # Condition settings (for condition steps)
    condition_type = models.CharField(max_length=50, blank=True)
    condition_config = models.JSONField(default=dict, blank=True)

    # Task settings (for task steps)
    task_description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sequence_steps"
        ordering = ["order"]
        unique_together = ["sequence", "order"]

    def __str__(self):
        return f"{self.sequence.name} - Step {self.order} ({self.step_type})"


class SequenceEnrollment(models.Model):
    """Enrollment of a lead in a sequence."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        PAUSED = "paused", "Paused"
        STOPPED = "stopped", "Stopped"
        BOUNCED = "bounced", "Bounced"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(
        EmailSequence, on_delete=models.CASCADE, related_name="enrollments"
    )
    lead = models.ForeignKey(
        "leads.Lead", on_delete=models.CASCADE, related_name="sequence_enrollments"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    # Progress
    current_step = models.ForeignKey(
        SequenceStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_enrollments",
    )
    last_step_completed = models.ForeignKey(
        SequenceStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_enrollments",
    )
    next_step_scheduled_at = models.DateTimeField(null=True, blank=True)

    # Tracking
    emails_sent = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)
    emails_replied = models.IntegerField(default=0)
    emails_bounced = models.IntegerField(default=0)

    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="enrolled_sequences",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    stop_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "sequence_enrollments"
        ordering = ["-enrolled_at"]
        unique_together = ["sequence", "lead"]

    def __str__(self):
        return f"{self.lead.full_name} in {self.sequence.name}"

    @property
    def open_rate(self):
        if self.emails_sent == 0:
            return 0
        return round(self.emails_opened / self.emails_sent * 100, 2)

    @property
    def click_rate(self):
        if self.emails_sent == 0:
            return 0
        return round(self.emails_clicked / self.emails_sent * 100, 2)

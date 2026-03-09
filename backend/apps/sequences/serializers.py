"""
Serializers for sequence models.
"""

from rest_framework import serializers

from .models import EmailSequence, SequenceEnrollment, SequenceStep


class SequenceStepSerializer(serializers.ModelSerializer):
    """Serializer for SequenceStep model."""

    class Meta:
        model = SequenceStep
        fields = [
            "id",
            "sequence",
            "order",
            "step_type",
            "subject",
            "body_html",
            "body_text",
            "delay_days",
            "delay_hours",
            "send_time",
            "condition_type",
            "condition_config",
            "task_description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SequenceEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for SequenceEnrollment model."""

    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_email = serializers.EmailField(source="lead.email", read_only=True)
    sequence_name = serializers.CharField(source="sequence.name", read_only=True)
    open_rate = serializers.FloatField(read_only=True)
    click_rate = serializers.FloatField(read_only=True)
    current_step_order = serializers.IntegerField(
        source="current_step.order", read_only=True, default=None
    )

    class Meta:
        model = SequenceEnrollment
        fields = [
            "id",
            "sequence",
            "sequence_name",
            "lead",
            "lead_name",
            "lead_email",
            "status",
            "current_step",
            "current_step_order",
            "last_step_completed",
            "next_step_scheduled_at",
            "emails_sent",
            "emails_opened",
            "emails_clicked",
            "emails_replied",
            "emails_bounced",
            "open_rate",
            "click_rate",
            "enrolled_by",
            "enrolled_at",
            "completed_at",
            "stopped_at",
            "stop_reason",
        ]
        read_only_fields = ["id", "enrolled_at", "completed_at"]


class EmailSequenceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing sequences."""

    step_count = serializers.IntegerField(read_only=True)
    active_enrollments = serializers.IntegerField(read_only=True)
    total_enrollments = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = EmailSequence
        fields = [
            "id",
            "name",
            "description",
            "status",
            "step_count",
            "active_enrollments",
            "total_enrollments",
            "tags",
            "created_by_name",
            "created_at",
            "updated_at",
        ]


class EmailSequenceDetailSerializer(serializers.ModelSerializer):
    """Full serializer for sequence detail with steps."""

    steps = SequenceStepSerializer(many=True, read_only=True)
    step_count = serializers.IntegerField(read_only=True)
    active_enrollments = serializers.IntegerField(read_only=True)
    total_enrollments = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = EmailSequence
        fields = [
            "id",
            "name",
            "description",
            "status",
            "send_as",
            "reply_to_email",
            "track_opens",
            "track_clicks",
            "stop_on_reply",
            "steps",
            "step_count",
            "active_enrollments",
            "total_enrollments",
            "tags",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class EnrollLeadSerializer(serializers.Serializer):
    """Serializer for enrolling a lead in a sequence."""

    lead_id = serializers.UUIDField()

    def validate_lead_id(self, value):
        from apps.leads.models import Lead

        try:
            Lead.objects.get(id=value)
        except Lead.DoesNotExist:
            raise serializers.ValidationError("Lead not found.")
        return value

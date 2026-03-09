"""
Serializers for lead-related models.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Lead, LeadActivity, LeadScore, LeadSource


class LeadSourceSerializer(serializers.ModelSerializer):
    """Serializer for LeadSource model."""

    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadSource
        fields = ["id", "name", "description", "is_active", "lead_count", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_lead_count(self, obj):
        return obj.leads.count()


class LeadScoreSerializer(serializers.ModelSerializer):
    """Serializer for LeadScore model."""

    class Meta:
        model = LeadScore
        fields = [
            "id",
            "lead",
            "demographic_score",
            "behavioral_score",
            "engagement_score",
            "firmographic_score",
            "total_score",
            "score_details",
            "calculated_at",
        ]
        read_only_fields = ["id", "calculated_at"]


class LeadActivitySerializer(serializers.ModelSerializer):
    """Serializer for LeadActivity model."""

    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True
    )

    class Meta:
        model = LeadActivity
        fields = [
            "id",
            "lead",
            "activity_type",
            "title",
            "description",
            "metadata",
            "performed_by",
            "performed_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LeadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing leads."""

    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    source_name = serializers.CharField(source="source.name", read_only=True, default=None)
    current_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "company",
            "status",
            "priority",
            "source_name",
            "assigned_to",
            "assigned_to_name",
            "current_score",
            "estimated_value",
            "last_contacted_at",
            "next_follow_up",
            "created_at",
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    """Full serializer for lead detail view."""

    assigned_to_details = UserSerializer(source="assigned_to", read_only=True)
    source_details = LeadSourceSerializer(source="source", read_only=True)
    current_score = serializers.IntegerField(read_only=True)
    recent_activities = serializers.SerializerMethodField()
    score_history = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "job_title",
            "industry",
            "website",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "status",
            "priority",
            "source",
            "source_details",
            "assigned_to",
            "assigned_to_details",
            "created_by",
            "estimated_value",
            "notes",
            "tags",
            "current_score",
            "last_contacted_at",
            "next_follow_up",
            "recent_activities",
            "score_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_recent_activities(self, obj):
        activities = obj.activities.select_related("performed_by")[:10]
        return LeadActivitySerializer(activities, many=True).data

    def get_score_history(self, obj):
        scores = obj.scores.all()[:10]
        return LeadScoreSerializer(scores, many=True).data


class LeadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new lead."""

    class Meta:
        model = Lead
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "company",
            "job_title",
            "industry",
            "website",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "status",
            "priority",
            "source",
            "assigned_to",
            "estimated_value",
            "notes",
            "tags",
            "next_follow_up",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

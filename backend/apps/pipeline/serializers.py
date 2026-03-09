"""
Serializers for pipeline-related models.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Deal, DealHistory, Pipeline, Stage


class StageSerializer(serializers.ModelSerializer):
    """Serializer for Stage model."""

    deal_count = serializers.IntegerField(read_only=True)
    total_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Stage
        fields = [
            "id",
            "pipeline",
            "name",
            "description",
            "order",
            "probability",
            "color",
            "is_active",
            "deal_count",
            "total_value",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class DealHistorySerializer(serializers.ModelSerializer):
    """Serializer for DealHistory model."""

    changed_by_name = serializers.CharField(
        source="changed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = DealHistory
        fields = [
            "id",
            "deal",
            "field_changed",
            "old_value",
            "new_value",
            "changed_by",
            "changed_by_name",
            "changed_at",
        ]
        read_only_fields = ["id", "changed_at"]


class DealListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing deals."""

    stage_name = serializers.CharField(source="stage.name", read_only=True)
    stage_color = serializers.CharField(source="stage.color", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    weighted_value = serializers.FloatField(read_only=True)
    days_in_stage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Deal
        fields = [
            "id",
            "title",
            "value",
            "currency",
            "stage",
            "stage_name",
            "stage_color",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_name",
            "contact_name",
            "company",
            "expected_close_date",
            "weighted_value",
            "days_in_stage",
            "tags",
            "created_at",
        ]


class DealDetailSerializer(serializers.ModelSerializer):
    """Full serializer for deal detail view."""

    stage_details = StageSerializer(source="stage", read_only=True)
    assigned_to_details = UserSerializer(source="assigned_to", read_only=True)
    weighted_value = serializers.FloatField(read_only=True)
    days_in_pipeline = serializers.IntegerField(read_only=True)
    days_in_stage = serializers.IntegerField(read_only=True)
    history = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            "id",
            "title",
            "description",
            "value",
            "currency",
            "pipeline",
            "stage",
            "stage_details",
            "status",
            "priority",
            "lead",
            "assigned_to",
            "assigned_to_details",
            "created_by",
            "contact_name",
            "contact_email",
            "company",
            "expected_close_date",
            "actual_close_date",
            "last_activity_at",
            "tags",
            "custom_fields",
            "loss_reason",
            "weighted_value",
            "days_in_pipeline",
            "days_in_stage",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_history(self, obj):
        history = obj.history.select_related("changed_by")[:20]
        return DealHistorySerializer(history, many=True).data


class DealCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a deal."""

    class Meta:
        model = Deal
        fields = [
            "title",
            "description",
            "value",
            "currency",
            "pipeline",
            "stage",
            "status",
            "priority",
            "lead",
            "assigned_to",
            "contact_name",
            "contact_email",
            "company",
            "expected_close_date",
            "tags",
            "custom_fields",
            "loss_reason",
        ]

    def validate(self, attrs):
        stage = attrs.get("stage")
        pipeline = attrs.get("pipeline")
        if stage and pipeline and stage.pipeline_id != pipeline.id:
            raise serializers.ValidationError(
                {"stage": "Stage does not belong to the selected pipeline."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class DealMoveSerializer(serializers.Serializer):
    """Serializer for moving a deal to a different stage."""

    stage_id = serializers.UUIDField()
    position = serializers.IntegerField(required=False, default=0)

    def validate_stage_id(self, value):
        try:
            Stage.objects.get(id=value)
        except Stage.DoesNotExist:
            raise serializers.ValidationError("Stage not found.")
        return value


class PipelineListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing pipelines."""

    total_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    deal_count = serializers.IntegerField(read_only=True)
    stage_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "total_value",
            "deal_count",
            "stage_count",
            "created_at",
        ]

    def get_stage_count(self, obj):
        return obj.stages.filter(is_active=True).count()


class PipelineDetailSerializer(serializers.ModelSerializer):
    """Full serializer with stages and deal summary."""

    stages = StageSerializer(many=True, read_only=True)
    total_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    deal_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Pipeline
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "stages",
            "total_value",
            "deal_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

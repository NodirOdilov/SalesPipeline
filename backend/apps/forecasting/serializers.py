"""
Serializers for forecasting models.
"""

from rest_framework import serializers

from .models import Forecast, ForecastPeriod


class ForecastPeriodSerializer(serializers.ModelSerializer):
    """Serializer for ForecastPeriod model."""

    class Meta:
        model = ForecastPeriod
        fields = [
            "id",
            "forecast",
            "period_start",
            "period_end",
            "label",
            "predicted_revenue",
            "actual_revenue",
            "deal_count",
            "weighted_value",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ForecastListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing forecasts."""

    accuracy = serializers.FloatField(read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Forecast
        fields = [
            "id",
            "name",
            "forecast_type",
            "status",
            "start_date",
            "end_date",
            "predicted_revenue",
            "best_case",
            "worst_case",
            "weighted_pipeline",
            "committed",
            "actual_revenue",
            "accuracy",
            "created_by_name",
            "created_at",
        ]


class ForecastDetailSerializer(serializers.ModelSerializer):
    """Full serializer for forecast detail."""

    accuracy = serializers.FloatField(read_only=True)
    periods = ForecastPeriodSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Forecast
        fields = [
            "id",
            "name",
            "forecast_type",
            "status",
            "pipeline",
            "team",
            "sales_rep",
            "start_date",
            "end_date",
            "predicted_revenue",
            "best_case",
            "worst_case",
            "weighted_pipeline",
            "committed",
            "actual_revenue",
            "accuracy",
            "assumptions",
            "notes",
            "calculation_details",
            "periods",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class GenerateForecastSerializer(serializers.Serializer):
    """Serializer for forecast generation request."""

    pipeline_id = serializers.UUIDField(required=False, allow_null=True)
    team_id = serializers.UUIDField(required=False, allow_null=True)
    sales_rep_id = serializers.UUIDField(required=False, allow_null=True)
    forecast_type = serializers.ChoiceField(
        choices=Forecast.ForecastType.choices,
        default=Forecast.ForecastType.MONTHLY,
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_date": "End date must be after start date."}
            )
        return attrs

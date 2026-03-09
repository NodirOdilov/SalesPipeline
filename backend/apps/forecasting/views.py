"""
Views for sales forecasting.
"""

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManager

from .models import Forecast
from .serializers import (
    ForecastDetailSerializer,
    ForecastListSerializer,
    GenerateForecastSerializer,
)
from .services import ForecastingService


class ForecastViewSet(viewsets.ModelViewSet):
    """CRUD for forecasts with generation support."""

    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["forecast_type", "status", "pipeline", "team", "sales_rep"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "created_at", "predicted_revenue"]
    ordering = ["-start_date"]

    def get_queryset(self):
        qs = Forecast.objects.select_related(
            "pipeline", "team", "sales_rep", "created_by"
        ).prefetch_related("periods")

        user = self.request.user
        if user.is_manager:
            return qs
        return qs.filter(sales_rep=user)

    def get_serializer_class(self):
        if self.action == "list":
            return ForecastListSerializer
        return ForecastDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "generate"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate a new forecast based on current pipeline data."""
        serializer = GenerateForecastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ForecastingService()
        forecast = service.generate_forecast(
            pipeline_id=serializer.validated_data.get("pipeline_id"),
            team_id=serializer.validated_data.get("team_id"),
            sales_rep_id=serializer.validated_data.get("sales_rep_id"),
            forecast_type=serializer.validated_data.get("forecast_type", "monthly"),
            start_date=serializer.validated_data.get("start_date"),
            end_date=serializer.validated_data.get("end_date"),
            created_by=request.user,
        )

        return Response(
            {
                "success": True,
                "message": "Forecast generated successfully.",
                "data": ForecastDetailSerializer(forecast).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def update_actuals(self, request, pk=None):
        """Update forecast with actual revenue data."""
        forecast = self.get_object()
        service = ForecastingService()
        updated = service.update_actuals(str(forecast.id))

        return Response(
            {
                "success": True,
                "message": "Forecast actuals updated.",
                "data": ForecastDetailSerializer(updated).data,
            }
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft forecast for approval."""
        forecast = self.get_object()
        if forecast.status != Forecast.Status.DRAFT:
            return Response(
                {"success": False, "message": "Only draft forecasts can be submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        forecast.status = Forecast.Status.SUBMITTED
        forecast.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Forecast submitted for approval.",
                "data": ForecastDetailSerializer(forecast).data,
            }
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a submitted forecast."""
        forecast = self.get_object()
        if forecast.status != Forecast.Status.SUBMITTED:
            return Response(
                {"success": False, "message": "Only submitted forecasts can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        forecast.status = Forecast.Status.APPROVED
        forecast.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Forecast approved.",
                "data": ForecastDetailSerializer(forecast).data,
            }
        )

    @action(detail=False, methods=["get"])
    def comparison(self, request):
        """Compare multiple forecasts side by side."""
        forecast_ids = request.query_params.getlist("ids")
        if not forecast_ids:
            return Response(
                {"success": False, "message": "Provide forecast IDs via ?ids=... query params."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        forecasts = self.get_queryset().filter(id__in=forecast_ids)
        data = ForecastListSerializer(forecasts, many=True).data

        return Response({"success": True, "data": data})

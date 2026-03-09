"""
Views for pipeline management: pipelines, stages, deals.
"""

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManager, IsSalesRepOrAbove

from .models import Deal, DealHistory, Pipeline, Stage
from .serializers import (
    DealCreateSerializer,
    DealDetailSerializer,
    DealHistorySerializer,
    DealListSerializer,
    DealMoveSerializer,
    PipelineDetailSerializer,
    PipelineListSerializer,
    StageSerializer,
)


class PipelineViewSet(viewsets.ModelViewSet):
    """CRUD for pipelines."""

    queryset = Pipeline.objects.prefetch_related("stages").all()
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    filterset_fields = ["is_active", "is_default"]

    def get_serializer_class(self):
        if self.action == "list":
            return PipelineListSerializer
        return PipelineDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def board(self, request, pk=None):
        """Get full board view with stages and their deals."""
        pipeline = self.get_object()
        stages = pipeline.stages.filter(is_active=True).order_by("order")

        board_data = []
        for stage in stages:
            deals = Deal.objects.filter(
                stage=stage, status=Deal.Status.OPEN
            ).select_related("assigned_to").order_by("-value")

            board_data.append(
                {
                    "stage": StageSerializer(stage).data,
                    "deals": DealListSerializer(deals, many=True).data,
                }
            )

        return Response(
            {
                "success": True,
                "data": {
                    "pipeline": PipelineListSerializer(pipeline).data,
                    "board": board_data,
                },
            }
        )


class StageViewSet(viewsets.ModelViewSet):
    """CRUD for pipeline stages."""

    queryset = Stage.objects.select_related("pipeline").all()
    serializer_class = StageSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filterset_fields = ["pipeline", "is_active"]
    ordering_fields = ["order", "name"]

    @action(detail=True, methods=["post"])
    def reorder(self, request, pk=None):
        """Update the order of a stage."""
        stage = self.get_object()
        new_order = request.data.get("order")
        if new_order is None:
            return Response(
                {"success": False, "message": "Order is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_order = stage.order
        stage.order = new_order
        stage.save(update_fields=["order"])

        # Shift other stages
        siblings = Stage.objects.filter(pipeline=stage.pipeline).exclude(pk=stage.pk)
        if new_order < old_order:
            siblings.filter(order__gte=new_order, order__lt=old_order).update(
                order=models.F("order") + 1
            )
        else:
            siblings.filter(order__gt=old_order, order__lte=new_order).update(
                order=models.F("order") - 1
            )

        return Response(
            {"success": True, "message": "Stage reordered.", "data": StageSerializer(stage).data}
        )


class DealViewSet(viewsets.ModelViewSet):
    """CRUD for deals with pipeline board support."""

    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filterset_fields = ["pipeline", "stage", "status", "priority", "assigned_to"]
    search_fields = ["title", "contact_name", "company"]
    ordering_fields = ["created_at", "value", "expected_close_date", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Deal.objects.select_related(
            "pipeline", "stage", "assigned_to", "lead"
        )
        user = self.request.user
        if user.is_manager:
            return qs
        return qs.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.action == "list":
            return DealListSerializer
        if self.action == "create":
            return DealCreateSerializer
        if self.action in ("update", "partial_update"):
            return DealCreateSerializer
        return DealDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        deal = self.get_object()
        old_values = {
            "stage": str(deal.stage_id),
            "status": deal.status,
            "value": str(deal.value),
            "assigned_to": str(deal.assigned_to_id) if deal.assigned_to else None,
        }

        updated_deal = serializer.save()

        # Record history for changed fields
        tracked_fields = ["stage", "status", "value", "assigned_to", "priority"]
        for field in tracked_fields:
            new_val = str(getattr(updated_deal, f"{field}_id" if field in ("stage", "assigned_to") else field, ""))
            old_val = old_values.get(field, "")
            if old_val != new_val:
                DealHistory.objects.create(
                    deal=updated_deal,
                    field_changed=field,
                    old_value=old_val or "",
                    new_value=new_val or "",
                    changed_by=self.request.user,
                )

    @action(detail=True, methods=["patch"])
    def move(self, request, pk=None):
        """Move a deal to a different stage (drag-and-drop support)."""
        deal = self.get_object()
        serializer = DealMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_stage = Stage.objects.get(id=serializer.validated_data["stage_id"])
        old_stage = deal.stage

        if old_stage.id != new_stage.id:
            DealHistory.objects.create(
                deal=deal,
                field_changed="stage",
                old_value=str(old_stage.id),
                new_value=str(new_stage.id),
                changed_by=request.user,
            )
            deal.stage = new_stage
            deal.last_activity_at = timezone.now()
            deal.save(update_fields=["stage", "last_activity_at", "updated_at"])

        return Response(
            {
                "success": True,
                "message": f"Deal moved to {new_stage.name}.",
                "data": DealDetailSerializer(deal).data,
            }
        )

    @action(detail=True, methods=["post"])
    def win(self, request, pk=None):
        """Mark a deal as won."""
        deal = self.get_object()
        deal.status = Deal.Status.WON
        deal.actual_close_date = timezone.now().date()
        deal.save(update_fields=["status", "actual_close_date", "updated_at"])

        DealHistory.objects.create(
            deal=deal,
            field_changed="status",
            old_value="open",
            new_value="won",
            changed_by=request.user,
        )

        return Response(
            {
                "success": True,
                "message": "Deal marked as won.",
                "data": DealDetailSerializer(deal).data,
            }
        )

    @action(detail=True, methods=["post"])
    def lose(self, request, pk=None):
        """Mark a deal as lost."""
        deal = self.get_object()
        deal.status = Deal.Status.LOST
        deal.actual_close_date = timezone.now().date()
        deal.loss_reason = request.data.get("loss_reason", "")
        deal.save(update_fields=["status", "actual_close_date", "loss_reason", "updated_at"])

        DealHistory.objects.create(
            deal=deal,
            field_changed="status",
            old_value="open",
            new_value="lost",
            changed_by=request.user,
        )

        return Response(
            {
                "success": True,
                "message": "Deal marked as lost.",
                "data": DealDetailSerializer(deal).data,
            }
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """Get the full history of a deal."""
        deal = self.get_object()
        history = deal.history.select_related("changed_by").all()
        serializer = DealHistorySerializer(history, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get deal summary statistics."""
        qs = self.get_queryset()
        open_deals = qs.filter(status=Deal.Status.OPEN)
        won_deals = qs.filter(status=Deal.Status.WON)
        lost_deals = qs.filter(status=Deal.Status.LOST)

        pipeline_id = request.query_params.get("pipeline")
        if pipeline_id:
            open_deals = open_deals.filter(pipeline_id=pipeline_id)
            won_deals = won_deals.filter(pipeline_id=pipeline_id)
            lost_deals = lost_deals.filter(pipeline_id=pipeline_id)

        summary = {
            "open": {
                "count": open_deals.count(),
                "total_value": float(
                    open_deals.aggregate(total=Sum("value"))["total"] or 0
                ),
            },
            "won": {
                "count": won_deals.count(),
                "total_value": float(
                    won_deals.aggregate(total=Sum("value"))["total"] or 0
                ),
            },
            "lost": {
                "count": lost_deals.count(),
                "total_value": float(
                    lost_deals.aggregate(total=Sum("value"))["total"] or 0
                ),
            },
            "win_rate": round(
                won_deals.count()
                / max(won_deals.count() + lost_deals.count(), 1)
                * 100,
                2,
            ),
        }

        return Response({"success": True, "data": summary})

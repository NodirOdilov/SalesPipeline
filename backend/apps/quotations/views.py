"""
Views for quotation management: quotations, line items, templates.
"""

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManager, IsSalesRepOrAbove

from .models import Quotation, QuotationLineItem, QuotationTemplate
from .serializers import (
    QuotationCreateSerializer,
    QuotationDetailSerializer,
    QuotationLineItemSerializer,
    QuotationListSerializer,
    QuotationTemplateSerializer,
)
from .services import QuotationService


class QuotationTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for quotation templates."""

    queryset = QuotationTemplate.objects.all()
    serializer_class = QuotationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    search_fields = ["name", "description"]
    filterset_fields = ["is_active", "is_default"]


class QuotationViewSet(viewsets.ModelViewSet):
    """CRUD for quotations with workflow actions."""

    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filterset_fields = ["status", "deal", "lead", "prepared_by", "currency"]
    search_fields = ["quote_number", "title", "customer_name", "customer_company"]
    ordering_fields = ["created_at", "total_amount", "valid_until"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Quotation.objects.select_related(
            "deal", "lead", "template", "prepared_by", "approved_by"
        ).prefetch_related("line_items")

        user = self.request.user
        if user.is_manager:
            return qs
        return qs.filter(prepared_by=user)

    def get_serializer_class(self):
        if self.action == "list":
            return QuotationListSerializer
        if self.action in ("create",):
            return QuotationCreateSerializer
        return QuotationDetailSerializer

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Mark a quotation as sent to the customer."""
        quotation = self.get_object()
        if quotation.status not in (Quotation.Status.DRAFT, Quotation.Status.REVISED):
            return Response(
                {"success": False, "message": "Only draft or revised quotations can be sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = Quotation.Status.SENT
        quotation.sent_at = timezone.now()
        quotation.save(update_fields=["status", "sent_at", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Quotation marked as sent.",
                "data": QuotationDetailSerializer(quotation).data,
            }
        )

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Mark a quotation as accepted by the customer."""
        quotation = self.get_object()
        if quotation.status not in (Quotation.Status.SENT, Quotation.Status.VIEWED):
            return Response(
                {"success": False, "message": "Only sent or viewed quotations can be accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quotation.status = Quotation.Status.ACCEPTED
        quotation.accepted_at = timezone.now()
        quotation.save(update_fields=["status", "accepted_at", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Quotation accepted.",
                "data": QuotationDetailSerializer(quotation).data,
            }
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Mark a quotation as rejected."""
        quotation = self.get_object()
        quotation.status = Quotation.Status.REJECTED
        quotation.rejected_at = timezone.now()
        quotation.rejection_reason = request.data.get("reason", "")
        quotation.save(
            update_fields=["status", "rejected_at", "rejection_reason", "updated_at"]
        )
        return Response(
            {
                "success": True,
                "message": "Quotation rejected.",
                "data": QuotationDetailSerializer(quotation).data,
            }
        )

    @action(detail=True, methods=["post"])
    def revise(self, request, pk=None):
        """Create a new revision of the quotation."""
        original = self.get_object()
        service = QuotationService()
        revised = service.create_revision(original, request.user)
        return Response(
            {
                "success": True,
                "message": f"Revision v{revised.version} created.",
                "data": QuotationDetailSerializer(revised).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        """Recalculate quotation totals from line items."""
        quotation = self.get_object()
        service = QuotationService()
        service.recalculate_totals(quotation)
        quotation.refresh_from_db()
        return Response(
            {
                "success": True,
                "message": "Totals recalculated.",
                "data": QuotationDetailSerializer(quotation).data,
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get summary statistics for quotations."""
        qs = self.get_queryset()
        from django.db.models import Avg, Count, Sum

        stats = {
            "total_quotations": qs.count(),
            "by_status": {},
            "total_value": float(
                qs.aggregate(total=Sum("total_amount"))["total"] or 0
            ),
            "average_value": float(
                qs.aggregate(avg=Avg("total_amount"))["avg"] or 0
            ),
        }
        for choice_value, choice_label in Quotation.Status.choices:
            status_qs = qs.filter(status=choice_value)
            stats["by_status"][choice_value] = {
                "count": status_qs.count(),
                "total_value": float(
                    status_qs.aggregate(total=Sum("total_amount"))["total"] or 0
                ),
            }

        return Response({"success": True, "data": stats})


class QuotationLineItemViewSet(viewsets.ModelViewSet):
    """CRUD for quotation line items."""

    serializer_class = QuotationLineItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filterset_fields = ["quotation", "product"]
    ordering_fields = ["sort_order", "unit_price"]

    def get_queryset(self):
        return QuotationLineItem.objects.select_related(
            "quotation", "product"
        ).all()

    def perform_create(self, serializer):
        item = serializer.save()
        service = QuotationService()
        service.recalculate_totals(item.quotation)

    def perform_update(self, serializer):
        item = serializer.save()
        service = QuotationService()
        service.recalculate_totals(item.quotation)

    def perform_destroy(self, instance):
        quotation = instance.quotation
        instance.delete()
        service = QuotationService()
        service.recalculate_totals(quotation)

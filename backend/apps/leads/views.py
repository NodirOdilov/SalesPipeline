"""
Views for lead management.
"""

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.accounts.permissions import IsSalesRepOrAbove

from .models import Lead, LeadActivity, LeadSource
from .serializers import (
    LeadActivitySerializer,
    LeadCreateSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    LeadSourceSerializer,
)
from .services import LeadScoringService


class LeadSourceViewSet(viewsets.ModelViewSet):
    """CRUD for lead sources."""

    queryset = LeadSource.objects.all()
    serializer_class = LeadSourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name"]
    filterset_fields = ["is_active"]


class LeadViewSet(viewsets.ModelViewSet):
    """CRUD for leads with scoring and activity tracking."""

    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "priority", "source", "assigned_to"]
    search_fields = ["first_name", "last_name", "email", "company"]
    ordering_fields = ["created_at", "updated_at", "estimated_value", "priority"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Lead.objects.select_related("source", "assigned_to", "created_by")
        user = self.request.user

        # Admins and managers see all leads
        if user.is_manager:
            return qs

        # Sales reps see only their assigned leads
        return qs.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        if self.action == "create":
            return LeadCreateSerializer
        if self.action in ("retrieve",):
            return LeadDetailSerializer
        return LeadCreateSerializer

    def perform_create(self, serializer):
        lead = serializer.save()
        # Calculate initial score
        scoring_service = LeadScoringService()
        scoring_service.calculate_score(lead)

    @action(detail=True, methods=["post"])
    def score(self, request, pk=None):
        """Recalculate the lead score."""
        lead = self.get_object()
        scoring_service = LeadScoringService()
        new_score = scoring_service.calculate_score(lead)
        return Response(
            {
                "success": True,
                "data": {
                    "lead_id": str(lead.id),
                    "total_score": new_score.total_score,
                    "demographic_score": new_score.demographic_score,
                    "behavioral_score": new_score.behavioral_score,
                    "engagement_score": new_score.engagement_score,
                    "firmographic_score": new_score.firmographic_score,
                    "details": new_score.score_details,
                },
            }
        )

    @action(detail=True, methods=["get"])
    def activities(self, request, pk=None):
        """Get all activities for a lead."""
        lead = self.get_object()
        activities = lead.activities.select_related("performed_by").all()
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = LeadActivitySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = LeadActivitySerializer(activities, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["post"])
    def add_activity(self, request, pk=None):
        """Log a new activity for a lead."""
        lead = self.get_object()
        serializer = LeadActivitySerializer(data={**request.data, "lead": lead.id})
        serializer.is_valid(raise_exception=True)
        serializer.save(performed_by=request.user)

        # Update last_contacted_at for contact-type activities
        contact_types = [
            LeadActivity.ActivityType.EMAIL_SENT,
            LeadActivity.ActivityType.CALL,
            LeadActivity.ActivityType.MEETING,
        ]
        if request.data.get("activity_type") in contact_types:
            lead.last_contacted_at = timezone.now()
            lead.save(update_fields=["last_contacted_at", "updated_at"])

        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert a lead (mark as converted and optionally create a deal)."""
        lead = self.get_object()
        if lead.status == Lead.Status.CONVERTED:
            return Response(
                {"success": False, "message": "Lead is already converted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead.status = Lead.Status.CONVERTED
        lead.save(update_fields=["status", "updated_at"])

        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.STATUS_CHANGE,
            title="Lead converted",
            performed_by=request.user,
            metadata={"old_status": lead.status, "new_status": "converted"},
        )

        return Response(
            {
                "success": True,
                "message": "Lead converted successfully.",
                "data": LeadDetailSerializer(lead).data,
            }
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get lead statistics for the current user's view."""
        qs = self.get_queryset()
        from django.db.models import Avg, Count, Sum

        stats = {
            "total": qs.count(),
            "by_status": dict(
                qs.values_list("status").annotate(count=Count("id")).values_list("status", "count")
            ),
            "by_priority": dict(
                qs.values_list("priority").annotate(count=Count("id")).values_list("priority", "count")
            ),
            "total_estimated_value": float(
                qs.aggregate(total=Sum("estimated_value"))["total"] or 0
            ),
            "avg_estimated_value": float(
                qs.aggregate(avg=Avg("estimated_value"))["avg"] or 0
            ),
        }
        return Response({"success": True, "data": stats})


class LeadActivityViewSet(viewsets.ModelViewSet):
    """CRUD for lead activities (global view)."""

    queryset = LeadActivity.objects.select_related("lead", "performed_by").all()
    serializer_class = LeadActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["lead", "activity_type", "performed_by"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)

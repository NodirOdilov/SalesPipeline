"""
Views for email sequences management.
"""

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsSalesRepOrAbove

from .models import EmailSequence, SequenceEnrollment, SequenceStep
from .serializers import (
    EmailSequenceDetailSerializer,
    EmailSequenceListSerializer,
    EnrollLeadSerializer,
    SequenceEnrollmentSerializer,
    SequenceStepSerializer,
)
from .tasks import enroll_lead_in_sequence


class EmailSequenceViewSet(viewsets.ModelViewSet):
    """CRUD for email sequences."""

    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filterset_fields = ["status"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        return EmailSequence.objects.select_related(
            "created_by", "send_as"
        ).prefetch_related("steps", "enrollments")

    def get_serializer_class(self):
        if self.action == "list":
            return EmailSequenceListSerializer
        return EmailSequenceDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate a sequence."""
        sequence = self.get_object()
        if sequence.steps.filter(is_active=True).count() == 0:
            return Response(
                {"success": False, "message": "Sequence must have at least one active step."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sequence.status = EmailSequence.Status.ACTIVE
        sequence.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "success": True,
                "message": "Sequence activated.",
                "data": EmailSequenceDetailSerializer(sequence).data,
            }
        )

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause a sequence."""
        sequence = self.get_object()
        sequence.status = EmailSequence.Status.PAUSED
        sequence.save(update_fields=["status", "updated_at"])
        return Response(
            {"success": True, "message": "Sequence paused."}
        )

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        """Enroll a lead in this sequence."""
        sequence = self.get_object()
        serializer = EnrollLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_id = str(serializer.validated_data["lead_id"])
        enroll_lead_in_sequence.delay(
            str(sequence.id), lead_id, str(request.user.id)
        )

        return Response(
            {
                "success": True,
                "message": "Lead enrollment initiated.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        """Get all enrollments for this sequence."""
        sequence = self.get_object()
        enrollments = sequence.enrollments.select_related("lead", "current_step").all()

        status_filter = request.query_params.get("status")
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)

        page = self.paginate_queryset(enrollments)
        if page is not None:
            serializer = SequenceEnrollmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SequenceEnrollmentSerializer(enrollments, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get performance statistics for this sequence."""
        sequence = self.get_object()
        enrollments = sequence.enrollments.all()

        from django.db.models import Avg, Sum

        stats_data = enrollments.aggregate(
            total_sent=Sum("emails_sent"),
            total_opened=Sum("emails_opened"),
            total_clicked=Sum("emails_clicked"),
            total_replied=Sum("emails_replied"),
            total_bounced=Sum("emails_bounced"),
        )

        total_sent = stats_data["total_sent"] or 0

        return Response(
            {
                "success": True,
                "data": {
                    "total_enrollments": enrollments.count(),
                    "active": enrollments.filter(status="active").count(),
                    "completed": enrollments.filter(status="completed").count(),
                    "stopped": enrollments.filter(status="stopped").count(),
                    "total_emails_sent": total_sent,
                    "total_opened": stats_data["total_opened"] or 0,
                    "total_clicked": stats_data["total_clicked"] or 0,
                    "total_replied": stats_data["total_replied"] or 0,
                    "total_bounced": stats_data["total_bounced"] or 0,
                    "open_rate": round(
                        (stats_data["total_opened"] or 0) / max(total_sent, 1) * 100, 2
                    ),
                    "click_rate": round(
                        (stats_data["total_clicked"] or 0) / max(total_sent, 1) * 100, 2
                    ),
                    "reply_rate": round(
                        (stats_data["total_replied"] or 0) / max(total_sent, 1) * 100, 2
                    ),
                    "bounce_rate": round(
                        (stats_data["total_bounced"] or 0) / max(total_sent, 1) * 100, 2
                    ),
                },
            }
        )


class SequenceStepViewSet(viewsets.ModelViewSet):
    """CRUD for sequence steps."""

    queryset = SequenceStep.objects.select_related("sequence").all()
    serializer_class = SequenceStepSerializer
    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    filterset_fields = ["sequence", "step_type", "is_active"]
    ordering = ["order"]


class SequenceEnrollmentViewSet(viewsets.ModelViewSet):
    """Manage sequence enrollments."""

    queryset = SequenceEnrollment.objects.select_related(
        "sequence", "lead", "current_step"
    ).all()
    serializer_class = SequenceEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["sequence", "lead", "status"]
    ordering = ["-enrolled_at"]

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause an enrollment."""
        enrollment = self.get_object()
        enrollment.status = SequenceEnrollment.Status.PAUSED
        enrollment.save(update_fields=["status"])
        return Response({"success": True, "message": "Enrollment paused."})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """Resume a paused enrollment."""
        enrollment = self.get_object()
        if enrollment.status != SequenceEnrollment.Status.PAUSED:
            return Response(
                {"success": False, "message": "Only paused enrollments can be resumed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        enrollment.status = SequenceEnrollment.Status.ACTIVE
        enrollment.save(update_fields=["status"])
        return Response({"success": True, "message": "Enrollment resumed."})

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        """Stop an enrollment permanently."""
        enrollment = self.get_object()
        enrollment.status = SequenceEnrollment.Status.STOPPED
        enrollment.stopped_at = timezone.now()
        enrollment.stop_reason = request.data.get("reason", "Manually stopped")
        enrollment.save(update_fields=["status", "stopped_at", "stop_reason"])
        return Response({"success": True, "message": "Enrollment stopped."})

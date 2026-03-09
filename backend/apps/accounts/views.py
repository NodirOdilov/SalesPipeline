"""
Views for account management: users, teams, sales reps.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SalesRep, SalesTeam
from .permissions import IsAdmin, IsManager, IsManagerOrOwner
from .serializers import (
    ChangePasswordSerializer,
    SalesRepListSerializer,
    SalesRepSerializer,
    SalesTeamSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "data": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Current user profile."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Change password for the current user."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"success": True, "message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class UserViewSet(viewsets.ModelViewSet):
    """Admin user management."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["created_at", "email", "first_name"]

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"success": True, "message": f"User {user.email} deactivated."}
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(
            {"success": True, "message": f"User {user.email} activated."}
        )


class SalesTeamViewSet(viewsets.ModelViewSet):
    """CRUD for sales teams."""

    queryset = SalesTeam.objects.select_related("manager").all()
    serializer_class = SalesTeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    search_fields = ["name"]
    filterset_fields = ["is_active"]

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        team = self.get_object()
        members = team.members.select_related("user").filter(is_active=True)
        serializer = SalesRepListSerializer(members, many=True)
        return Response({"success": True, "data": serializer.data})


class SalesRepViewSet(viewsets.ModelViewSet):
    """CRUD for sales representatives."""

    queryset = SalesRep.objects.select_related("user", "team").all()
    serializer_class = SalesRepSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["team", "is_active", "quota_period"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["quota", "hire_date", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return SalesRepListSerializer
        return SalesRepSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        """Get performance summary for a sales rep."""
        rep = self.get_object()
        from apps.pipeline.models import Deal

        deals = Deal.objects.filter(assigned_to=rep.user)
        won_deals = deals.filter(status="won")
        lost_deals = deals.filter(status="lost")

        from django.db.models import Sum

        total_revenue = won_deals.aggregate(total=Sum("value"))["total"] or 0
        quota_attainment = (
            (total_revenue / rep.quota * 100) if rep.quota > 0 else 0
        )

        return Response(
            {
                "success": True,
                "data": {
                    "rep_id": str(rep.id),
                    "full_name": rep.full_name,
                    "total_deals": deals.count(),
                    "won_deals": won_deals.count(),
                    "lost_deals": lost_deals.count(),
                    "open_deals": deals.filter(status="open").count(),
                    "total_revenue": float(total_revenue),
                    "quota": float(rep.quota),
                    "quota_attainment": round(float(quota_attainment), 2),
                    "win_rate": round(
                        won_deals.count()
                        / max(won_deals.count() + lost_deals.count(), 1)
                        * 100,
                        2,
                    ),
                },
            }
        )

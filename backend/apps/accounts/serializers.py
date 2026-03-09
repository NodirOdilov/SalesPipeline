"""
Serializers for account-related models.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import SalesRep, SalesTeam

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (read operations)."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "phone",
            "avatar",
            "timezone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
            "phone",
            "timezone",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "timezone",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs


class SalesTeamSerializer(serializers.ModelSerializer):
    """Serializer for SalesTeam model."""

    manager_name = serializers.CharField(source="manager.get_full_name", read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    total_quota = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = SalesTeam
        fields = [
            "id",
            "name",
            "description",
            "manager",
            "manager_name",
            "member_count",
            "total_quota",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SalesRepSerializer(serializers.ModelSerializer):
    """Serializer for SalesRep model."""

    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    user_details = UserSerializer(source="user", read_only=True)

    class Meta:
        model = SalesRep
        fields = [
            "id",
            "user",
            "user_details",
            "team",
            "team_name",
            "full_name",
            "email",
            "title",
            "quota",
            "quota_period",
            "hire_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SalesRepListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing sales reps."""

    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = SalesRep
        fields = [
            "id",
            "full_name",
            "email",
            "team_name",
            "title",
            "quota",
            "quota_period",
            "is_active",
        ]

"""
URL patterns for the accounts app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChangePasswordView,
    ProfileView,
    RegisterView,
    SalesRepViewSet,
    SalesTeamViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"teams", SalesTeamViewSet, basename="team")
router.register(r"reps", SalesRepViewSet, basename="salesrep")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("", include(router.urls)),
]

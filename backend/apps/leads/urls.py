"""
URL patterns for the leads app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LeadActivityViewSet, LeadSourceViewSet, LeadViewSet

router = DefaultRouter()
router.register(r"sources", LeadSourceViewSet, basename="leadsource")
router.register(r"activities", LeadActivityViewSet, basename="leadactivity")
router.register(r"", LeadViewSet, basename="lead")

urlpatterns = [
    path("", include(router.urls)),
]

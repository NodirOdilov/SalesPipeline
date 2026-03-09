"""
URL patterns for the sequences app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EmailSequenceViewSet, SequenceEnrollmentViewSet, SequenceStepViewSet

router = DefaultRouter()
router.register(r"sequences", EmailSequenceViewSet, basename="emailsequence")
router.register(r"steps", SequenceStepViewSet, basename="sequencestep")
router.register(r"enrollments", SequenceEnrollmentViewSet, basename="sequenceenrollment")

urlpatterns = [
    path("", include(router.urls)),
]

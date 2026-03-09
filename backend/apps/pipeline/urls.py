"""
URL patterns for the pipeline app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DealViewSet, PipelineViewSet, StageViewSet

router = DefaultRouter()
router.register(r"pipelines", PipelineViewSet, basename="pipeline")
router.register(r"stages", StageViewSet, basename="stage")
router.register(r"deals", DealViewSet, basename="deal")

urlpatterns = [
    path("", include(router.urls)),
]

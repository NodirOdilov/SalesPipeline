"""
URL routing for quotation endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    QuotationLineItemViewSet,
    QuotationTemplateViewSet,
    QuotationViewSet,
)

router = DefaultRouter()
router.register(r"templates", QuotationTemplateViewSet, basename="quotation-template")
router.register(r"line-items", QuotationLineItemViewSet, basename="quotation-line-item")
router.register(r"", QuotationViewSet, basename="quotation")

urlpatterns = [
    path("", include(router.urls)),
]

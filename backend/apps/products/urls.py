"""
URL routing for product catalog endpoints.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PriceBookEntryViewSet,
    PriceBookViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
)

router = DefaultRouter()
router.register(r"categories", ProductCategoryViewSet, basename="product-category")
router.register(r"price-books", PriceBookViewSet, basename="price-book")
router.register(
    r"price-book-entries", PriceBookEntryViewSet, basename="price-book-entry"
)
router.register(r"", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
]

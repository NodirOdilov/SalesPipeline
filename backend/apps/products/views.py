"""
Views for the product catalog: products, categories, price books.
"""

from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsManager, IsSalesRepOrAbove

from .models import PriceBook, PriceBookEntry, Product, ProductCategory
from .serializers import (
    PriceBookEntrySerializer,
    PriceBookSerializer,
    ProductCategorySerializer,
    ProductCreateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for product categories."""

    queryset = ProductCategory.objects.annotate(
        active_products=Count("products", filter=Q(products__is_active=True))
    ).all()
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["name", "description"]
    filterset_fields = ["is_active", "parent"]
    ordering_fields = ["name", "sort_order", "created_at"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return the full category tree with nesting."""
        root_categories = self.get_queryset().filter(parent__isnull=True, is_active=True)
        tree = []
        for cat in root_categories:
            tree.append(self._build_node(cat))
        return Response({"success": True, "data": tree})

    def _build_node(self, category):
        children = category.children.filter(is_active=True).order_by("sort_order")
        node = ProductCategorySerializer(category).data
        node["children"] = [self._build_node(child) for child in children]
        return node


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD for products with catalog and pricing features."""

    permission_classes = [permissions.IsAuthenticated, IsSalesRepOrAbove]
    search_fields = ["name", "sku", "description"]
    filterset_fields = ["category", "product_type", "billing_frequency", "is_active"]
    ordering_fields = ["name", "unit_price", "created_at", "sku"]
    ordering = ["name"]

    def get_queryset(self):
        return Product.objects.select_related("category", "created_by").all()

    def get_serializer_class(self):
        if self.action == "list":
            return ProductListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ProductCreateSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAuthenticated(), IsManager()]
        return [permissions.IsAuthenticated(), IsSalesRepOrAbove()]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Return products with low stock levels."""
        products = self.get_queryset().filter(
            track_inventory=True, stock_quantity__lte=5, is_active=True
        )
        serializer = ProductListSerializer(products, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["get"])
    def pricing(self, request, pk=None):
        """Get all pricing entries for a product across price books."""
        product = self.get_object()
        entries = product.price_entries.filter(
            is_active=True, price_book__is_active=True
        ).select_related("price_book")
        serializer = PriceBookEntrySerializer(entries, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def search_catalog(self, request):
        """Full-text search across the product catalog."""
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response(
                {"success": False, "message": "Search query must be at least 2 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        products = self.get_queryset().filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__contains=[query]),
            is_active=True,
        )[:50]

        serializer = ProductListSerializer(products, many=True)
        return Response({"success": True, "data": serializer.data})


class PriceBookViewSet(viewsets.ModelViewSet):
    """CRUD for price books."""

    queryset = PriceBook.objects.prefetch_related("entries").all()
    serializer_class = PriceBookSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    search_fields = ["name"]
    filterset_fields = ["is_active", "is_default", "currency"]
    ordering_fields = ["name", "created_at"]

    @action(detail=True, methods=["get"])
    def entries(self, request, pk=None):
        """List all entries in a price book."""
        price_book = self.get_object()
        entries = price_book.entries.filter(is_active=True).select_related("product")
        serializer = PriceBookEntrySerializer(entries, many=True)
        return Response({"success": True, "data": serializer.data})


class PriceBookEntryViewSet(viewsets.ModelViewSet):
    """CRUD for price book entries."""

    queryset = PriceBookEntry.objects.select_related("price_book", "product").all()
    serializer_class = PriceBookEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]
    filterset_fields = ["price_book", "product", "is_active"]
    ordering_fields = ["unit_price", "product__name"]

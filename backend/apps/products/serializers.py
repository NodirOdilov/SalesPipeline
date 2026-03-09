"""
Serializers for product catalog models.
"""

from rest_framework import serializers

from .models import PriceBook, PriceBookEntry, Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for ProductCategory model."""

    full_path = serializers.CharField(read_only=True)
    product_count = serializers.IntegerField(read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "parent",
            "is_active",
            "sort_order",
            "full_path",
            "product_count",
            "children_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()

    def validate_parent(self, value):
        if value and value.pk == self.instance.pk if self.instance else False:
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing products."""

    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    margin = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "category",
            "category_name",
            "product_type",
            "billing_frequency",
            "unit_price",
            "currency",
            "margin",
            "is_active",
            "stock_quantity",
            "is_low_stock",
            "tags",
            "created_at",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail view."""

    category_details = ProductCategorySerializer(source="category", read_only=True)
    margin = serializers.FloatField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    price_entries = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "description",
            "category",
            "category_details",
            "product_type",
            "billing_frequency",
            "unit_price",
            "cost_price",
            "currency",
            "tax_rate",
            "margin",
            "is_active",
            "is_taxable",
            "stock_quantity",
            "track_inventory",
            "is_low_stock",
            "image_url",
            "external_id",
            "features",
            "specifications",
            "tags",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_price_entries(self, obj):
        entries = obj.price_entries.filter(is_active=True).select_related("price_book")
        return PriceBookEntrySerializer(entries, many=True).data


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating a product."""

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "description",
            "category",
            "product_type",
            "billing_frequency",
            "unit_price",
            "cost_price",
            "currency",
            "tax_rate",
            "is_active",
            "is_taxable",
            "stock_quantity",
            "track_inventory",
            "image_url",
            "external_id",
            "features",
            "specifications",
            "tags",
        ]

    def validate_sku(self, value):
        qs = Product.objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class PriceBookSerializer(serializers.ModelSerializer):
    """Serializer for PriceBook model."""

    entry_count = serializers.SerializerMethodField()

    class Meta:
        model = PriceBook
        fields = [
            "id",
            "name",
            "description",
            "is_default",
            "is_active",
            "currency",
            "valid_from",
            "valid_until",
            "entry_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_entry_count(self, obj):
        return obj.entries.filter(is_active=True).count()

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class PriceBookEntrySerializer(serializers.ModelSerializer):
    """Serializer for PriceBookEntry model."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    price_book_name = serializers.CharField(source="price_book.name", read_only=True)
    effective_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = PriceBookEntry
        fields = [
            "id",
            "price_book",
            "price_book_name",
            "product",
            "product_name",
            "unit_price",
            "minimum_quantity",
            "maximum_quantity",
            "discount_percent",
            "effective_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

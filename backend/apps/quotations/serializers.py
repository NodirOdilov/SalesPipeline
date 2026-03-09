"""
Serializers for quotation models.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Quotation, QuotationLineItem, QuotationTemplate


class QuotationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for QuotationTemplate model."""

    class Meta:
        model = QuotationTemplate
        fields = [
            "id",
            "name",
            "description",
            "header_html",
            "footer_html",
            "terms_and_conditions",
            "is_default",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class QuotationLineItemSerializer(serializers.ModelSerializer):
    """Serializer for QuotationLineItem model."""

    product_name = serializers.CharField(
        source="product.name", read_only=True, default=None
    )
    line_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    net_total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    tax_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = QuotationLineItem
        fields = [
            "id",
            "quotation",
            "product",
            "product_name",
            "description",
            "quantity",
            "unit_price",
            "discount_percent",
            "tax_rate",
            "line_total",
            "discount_amount",
            "net_total",
            "tax_amount",
            "total",
            "sort_order",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class QuotationLineItemCreateSerializer(serializers.ModelSerializer):
    """Serializer used when creating line items inline with a quotation."""

    class Meta:
        model = QuotationLineItem
        fields = [
            "product",
            "description",
            "quantity",
            "unit_price",
            "discount_percent",
            "tax_rate",
            "sort_order",
            "notes",
        ]


class QuotationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing quotations."""

    prepared_by_name = serializers.CharField(
        source="prepared_by.get_full_name", read_only=True, default=None
    )
    line_item_count = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id",
            "quote_number",
            "title",
            "status",
            "customer_name",
            "customer_company",
            "deal",
            "subtotal",
            "total_amount",
            "currency",
            "valid_until",
            "is_expired",
            "prepared_by",
            "prepared_by_name",
            "line_item_count",
            "version",
            "created_at",
        ]


class QuotationDetailSerializer(serializers.ModelSerializer):
    """Full serializer for quotation detail view."""

    prepared_by_details = UserSerializer(source="prepared_by", read_only=True)
    approved_by_details = UserSerializer(source="approved_by", read_only=True)
    line_items = QuotationLineItemSerializer(many=True, read_only=True)
    template_details = QuotationTemplateSerializer(source="template", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    revision_count = serializers.SerializerMethodField()

    class Meta:
        model = Quotation
        fields = [
            "id",
            "quote_number",
            "title",
            "status",
            "deal",
            "lead",
            "template",
            "template_details",
            "customer_name",
            "customer_email",
            "customer_company",
            "customer_address",
            "customer_phone",
            "subtotal",
            "discount_amount",
            "discount_percent",
            "tax_amount",
            "total_amount",
            "currency",
            "valid_until",
            "is_expired",
            "payment_terms",
            "terms_and_conditions",
            "notes",
            "internal_notes",
            "sent_at",
            "viewed_at",
            "accepted_at",
            "rejected_at",
            "rejection_reason",
            "version",
            "parent_quotation",
            "revision_count",
            "prepared_by",
            "prepared_by_details",
            "approved_by",
            "approved_by_details",
            "line_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "quote_number",
            "prepared_by",
            "created_at",
            "updated_at",
        ]

    def get_revision_count(self, obj):
        return obj.revisions.count()


class QuotationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new quotation."""

    line_items = QuotationLineItemCreateSerializer(many=True, required=False)

    class Meta:
        model = Quotation
        fields = [
            "title",
            "deal",
            "lead",
            "template",
            "customer_name",
            "customer_email",
            "customer_company",
            "customer_address",
            "customer_phone",
            "discount_percent",
            "currency",
            "valid_until",
            "payment_terms",
            "terms_and_conditions",
            "notes",
            "internal_notes",
            "line_items",
        ]

    def create(self, validated_data):
        line_items_data = validated_data.pop("line_items", [])
        validated_data["prepared_by"] = self.context["request"].user

        # Generate quote number
        from django.utils import timezone

        now = timezone.now()
        count = Quotation.objects.filter(
            created_at__year=now.year, created_at__month=now.month
        ).count()
        validated_data["quote_number"] = (
            f"QT-{now.strftime('%Y%m')}-{count + 1:04d}"
        )

        quotation = Quotation.objects.create(**validated_data)

        # Create line items and recalculate totals
        for idx, item_data in enumerate(line_items_data):
            item_data["sort_order"] = item_data.get("sort_order", idx)
            QuotationLineItem.objects.create(quotation=quotation, **item_data)

        self._recalculate_totals(quotation)
        return quotation

    def _recalculate_totals(self, quotation):
        """Recalculate quotation totals from line items."""
        from decimal import Decimal

        subtotal = Decimal("0")
        tax_total = Decimal("0")

        for item in quotation.line_items.all():
            subtotal += item.net_total
            tax_total += item.tax_amount

        quotation.subtotal = subtotal
        quotation.tax_amount = tax_total

        if quotation.discount_percent:
            quotation.discount_amount = subtotal * (
                quotation.discount_percent / Decimal("100")
            )
        else:
            quotation.discount_amount = Decimal("0")

        quotation.total_amount = subtotal - quotation.discount_amount + tax_total
        quotation.save(
            update_fields=[
                "subtotal",
                "discount_amount",
                "tax_amount",
                "total_amount",
                "updated_at",
            ]
        )

"""
Product catalog models: ProductCategory, Product, PriceBook, PriceBookEntry.
"""

import uuid

from django.conf import settings
from django.db import models


class ProductCategory(models.Model):
    """Hierarchical product category for organizing the catalog."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_categories"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "Product categories"

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        """Return the full category path, e.g. 'Software > CRM > Enterprise'."""
        parts = [self.name]
        current = self.parent
        while current is not None:
            parts.insert(0, current.name)
            current = current.parent
        return " > ".join(parts)

    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    """Product or service available for sale."""

    class ProductType(models.TextChoices):
        PRODUCT = "product", "Product"
        SERVICE = "service", "Service"
        SUBSCRIPTION = "subscription", "Subscription"
        ADDON = "addon", "Add-on"

    class BillingFrequency(models.TextChoices):
        ONE_TIME = "one_time", "One-time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    product_type = models.CharField(
        max_length=20, choices=ProductType.choices, default=ProductType.PRODUCT
    )
    billing_frequency = models.CharField(
        max_length=20,
        choices=BillingFrequency.choices,
        default=BillingFrequency.ONE_TIME,
    )

    # Pricing
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Inventory
    is_active = models.BooleanField(default=True)
    is_taxable = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0)
    track_inventory = models.BooleanField(default=False)

    # Media
    image_url = models.URLField(blank=True)
    external_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Metadata
    features = models.JSONField(default=list, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["product_type"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def margin(self):
        """Gross margin percentage."""
        if self.unit_price and self.cost_price:
            return round(
                float(self.unit_price - self.cost_price) / float(self.unit_price) * 100,
                2,
            )
        return 0

    @property
    def is_low_stock(self):
        return self.track_inventory and self.stock_quantity <= 5


class PriceBook(models.Model):
    """Named pricing tier for different customer segments or regions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    currency = models.CharField(max_length=3, default="USD")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_price_books",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "price_books"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            PriceBook.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class PriceBookEntry(models.Model):
    """Override pricing for a product within a specific price book."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_book = models.ForeignKey(
        PriceBook, on_delete=models.CASCADE, related_name="entries"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_entries"
    )
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    minimum_quantity = models.IntegerField(default=1)
    maximum_quantity = models.IntegerField(null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "price_book_entries"
        ordering = ["product__name"]
        unique_together = ["price_book", "product", "minimum_quantity"]

    def __str__(self):
        return f"{self.price_book.name} - {self.product.name}: {self.unit_price}"

    @property
    def effective_price(self):
        """Price after applying discount."""
        if self.discount_percent:
            discount = self.unit_price * (self.discount_percent / 100)
            return self.unit_price - discount
        return self.unit_price

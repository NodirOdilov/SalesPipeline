"""
Quotation models: Quotation, QuotationLineItem, QuotationTemplate.
"""

import uuid

from django.conf import settings
from django.db import models


class QuotationTemplate(models.Model):
    """Reusable quotation template with predefined layout and terms."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    header_html = models.TextField(blank=True, help_text="HTML for the quotation header section.")
    footer_html = models.TextField(blank=True, help_text="HTML for the quotation footer section.")
    terms_and_conditions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation_templates"
        ordering = ["-is_default", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            QuotationTemplate.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class Quotation(models.Model):
    """Sales quotation / proposal linked to a deal."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        REVISED = "revised", "Revised"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quote_number = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=300)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    # Related entities
    deal = models.ForeignKey(
        "pipeline.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotations",
    )
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotations",
    )
    template = models.ForeignKey(
        QuotationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotations",
    )

    # Customer info (copied from deal/lead for snapshot)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()
    customer_company = models.CharField(max_length=200, blank=True)
    customer_address = models.TextField(blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)

    # Financial totals
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")

    # Terms
    valid_until = models.DateField(null=True, blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)
    terms_and_conditions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Version control
    version = models.IntegerField(default=1)
    parent_quotation = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisions",
    )

    # Ownership
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="prepared_quotations",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quotations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["deal"]),
            models.Index(fields=["prepared_by"]),
            models.Index(fields=["valid_until"]),
        ]

    def __str__(self):
        return f"{self.quote_number} - {self.title}"

    @property
    def is_expired(self):
        from django.utils import timezone
        if self.valid_until:
            return timezone.now().date() > self.valid_until
        return False

    @property
    def line_item_count(self):
        return self.line_items.count()


class QuotationLineItem(models.Model):
    """Individual line item within a quotation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quotation = models.ForeignKey(
        Quotation, on_delete=models.CASCADE, related_name="line_items"
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotation_line_items",
    )

    # Line item details (may differ from product defaults)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    sort_order = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quotation_line_items"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.quotation.quote_number} - {self.description}"

    @property
    def line_total(self):
        """Gross total before discount and tax."""
        return self.quantity * self.unit_price

    @property
    def discount_amount(self):
        return self.line_total * (self.discount_percent / 100)

    @property
    def net_total(self):
        """Total after discount, before tax."""
        return self.line_total - self.discount_amount

    @property
    def tax_amount(self):
        return self.net_total * (self.tax_rate / 100)

    @property
    def total(self):
        """Final total including tax."""
        return self.net_total + self.tax_amount

"""
Quotation service layer.
Handles revision creation, total recalculation, and quotation lifecycle logic.
"""

import logging
from decimal import Decimal

from django.utils import timezone

from .models import Quotation, QuotationLineItem

logger = logging.getLogger(__name__)


class QuotationService:
    """Service for quotation operations beyond simple CRUD."""

    def create_revision(self, original: Quotation, user) -> Quotation:
        """
        Create a new revision of an existing quotation.
        Copies all data and line items, increments version, and marks the
        original as revised.
        """
        # Mark original as revised
        original.status = Quotation.Status.REVISED
        original.save(update_fields=["status", "updated_at"])

        # Generate new quote number
        now = timezone.now()
        count = Quotation.objects.filter(
            created_at__year=now.year, created_at__month=now.month
        ).count()
        new_quote_number = f"QT-{now.strftime('%Y%m')}-{count + 1:04d}"

        # Clone the quotation
        revised = Quotation.objects.create(
            quote_number=new_quote_number,
            title=original.title,
            status=Quotation.Status.DRAFT,
            deal=original.deal,
            lead=original.lead,
            template=original.template,
            customer_name=original.customer_name,
            customer_email=original.customer_email,
            customer_company=original.customer_company,
            customer_address=original.customer_address,
            customer_phone=original.customer_phone,
            subtotal=original.subtotal,
            discount_amount=original.discount_amount,
            discount_percent=original.discount_percent,
            tax_amount=original.tax_amount,
            total_amount=original.total_amount,
            currency=original.currency,
            valid_until=original.valid_until,
            payment_terms=original.payment_terms,
            terms_and_conditions=original.terms_and_conditions,
            notes=original.notes,
            internal_notes=original.internal_notes,
            version=original.version + 1,
            parent_quotation=original,
            prepared_by=user,
        )

        # Clone line items
        for item in original.line_items.all():
            QuotationLineItem.objects.create(
                quotation=revised,
                product=item.product,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                tax_rate=item.tax_rate,
                sort_order=item.sort_order,
                notes=item.notes,
            )

        logger.info(
            f"Quotation revision created: {revised.quote_number} "
            f"(v{revised.version}) from {original.quote_number}"
        )

        return revised

    def recalculate_totals(self, quotation: Quotation) -> Quotation:
        """
        Recalculate subtotal, tax, discount, and total from line items.
        """
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

        logger.info(
            f"Quotation {quotation.quote_number} totals recalculated: "
            f"subtotal={subtotal}, tax={tax_total}, total={quotation.total_amount}"
        )

        return quotation

    def expire_overdue_quotations(self) -> int:
        """
        Mark sent/viewed quotations whose valid_until date has passed
        as expired. Returns count of newly expired quotations.
        """
        today = timezone.now().date()
        expired_qs = Quotation.objects.filter(
            status__in=[Quotation.Status.SENT, Quotation.Status.VIEWED],
            valid_until__lt=today,
        )
        count = expired_qs.count()
        expired_qs.update(status=Quotation.Status.EXPIRED, updated_at=timezone.now())

        if count > 0:
            logger.info(f"Expired {count} overdue quotations.")

        return count

    def calculate_conversion_rate(self, start_date=None, end_date=None) -> dict:
        """
        Calculate quotation-to-deal conversion metrics within a date range.
        """
        qs = Quotation.objects.all()
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        total = qs.count()
        accepted = qs.filter(status=Quotation.Status.ACCEPTED).count()
        rejected = qs.filter(status=Quotation.Status.REJECTED).count()
        expired = qs.filter(status=Quotation.Status.EXPIRED).count()
        pending = qs.filter(
            status__in=[Quotation.Status.DRAFT, Quotation.Status.SENT, Quotation.Status.VIEWED]
        ).count()

        conversion_rate = round(accepted / max(total, 1) * 100, 2)

        return {
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "expired": expired,
            "pending": pending,
            "conversion_rate": conversion_rate,
        }

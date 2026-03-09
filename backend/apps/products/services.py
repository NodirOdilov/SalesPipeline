"""
Product catalog service layer.
Handles pricing resolution, inventory management, and catalog operations.
"""

import logging
from decimal import Decimal
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from .models import PriceBook, PriceBookEntry, Product

logger = logging.getLogger(__name__)


class ProductService:
    """Service for product operations beyond simple CRUD."""

    def resolve_price(
        self,
        product_id: str,
        quantity: int = 1,
        price_book_id: Optional[str] = None,
        currency: str = "USD",
    ) -> dict:
        """
        Resolve the effective unit price for a product based on price book
        and quantity. Falls back to the product's list price if no price
        book entry matches.
        """
        product = Product.objects.get(id=product_id)

        # Try specific price book first
        if price_book_id:
            entry = self._find_price_entry(price_book_id, product_id, quantity)
            if entry:
                return self._build_price_response(product, entry, quantity)

        # Try the default price book
        default_book = PriceBook.objects.filter(
            is_default=True, is_active=True, currency=currency
        ).first()
        if default_book:
            entry = self._find_price_entry(str(default_book.id), product_id, quantity)
            if entry:
                return self._build_price_response(product, entry, quantity)

        # Fall back to product list price
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "sku": product.sku,
            "unit_price": float(product.unit_price),
            "quantity": quantity,
            "subtotal": float(product.unit_price * quantity),
            "discount_percent": 0,
            "discount_amount": 0,
            "price_source": "list_price",
            "currency": product.currency,
        }

    def _find_price_entry(
        self, price_book_id: str, product_id: str, quantity: int
    ) -> Optional[PriceBookEntry]:
        """Find the best matching price book entry for the given quantity."""
        return (
            PriceBookEntry.objects.filter(
                price_book_id=price_book_id,
                product_id=product_id,
                is_active=True,
                minimum_quantity__lte=quantity,
            )
            .filter(Q(maximum_quantity__gte=quantity) | Q(maximum_quantity__isnull=True))
            .order_by("-minimum_quantity")
            .first()
        )

    def _build_price_response(
        self, product: Product, entry: PriceBookEntry, quantity: int
    ) -> dict:
        """Build the pricing response from a price book entry."""
        effective = entry.effective_price
        discount_amount = float(entry.unit_price - effective) * quantity
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "sku": product.sku,
            "unit_price": float(effective),
            "list_price": float(entry.unit_price),
            "quantity": quantity,
            "subtotal": float(effective * quantity),
            "discount_percent": float(entry.discount_percent),
            "discount_amount": round(discount_amount, 2),
            "price_source": "price_book",
            "price_book_id": str(entry.price_book_id),
            "currency": product.currency,
        }

    def check_inventory(self, product_id: str, quantity: int) -> dict:
        """
        Check whether the requested quantity is available in stock.
        Returns availability status and details.
        """
        product = Product.objects.get(id=product_id)

        if not product.track_inventory:
            return {
                "available": True,
                "product_id": str(product.id),
                "requested": quantity,
                "in_stock": None,
                "tracking_enabled": False,
            }

        available = product.stock_quantity >= quantity
        return {
            "available": available,
            "product_id": str(product.id),
            "requested": quantity,
            "in_stock": product.stock_quantity,
            "remaining_after": max(product.stock_quantity - quantity, 0) if available else 0,
            "tracking_enabled": True,
        }

    def adjust_stock(self, product_id: str, quantity_delta: int, reason: str = "") -> Product:
        """
        Adjust stock quantity by a delta (positive to add, negative to remove).
        Returns the updated product.
        """
        product = Product.objects.select_for_update().get(id=product_id)

        if not product.track_inventory:
            logger.warning(
                f"Stock adjustment requested for product {product_id} "
                f"but inventory tracking is disabled."
            )
            return product

        new_quantity = product.stock_quantity + quantity_delta
        if new_quantity < 0:
            raise ValueError(
                f"Insufficient stock: current={product.stock_quantity}, "
                f"requested delta={quantity_delta}"
            )

        product.stock_quantity = new_quantity
        product.save(update_fields=["stock_quantity", "updated_at"])

        logger.info(
            f"Stock adjusted for {product.sku}: {product.stock_quantity - quantity_delta} "
            f"-> {new_quantity} (delta={quantity_delta}, reason={reason})"
        )

        return product

    def bulk_update_prices(
        self, price_book_id: str, adjustment_percent: Decimal
    ) -> int:
        """
        Apply a percentage adjustment to all entries in a price book.
        Returns the number of entries updated.
        """
        entries = PriceBookEntry.objects.filter(
            price_book_id=price_book_id, is_active=True
        )
        count = 0
        for entry in entries:
            multiplier = Decimal("1") + (adjustment_percent / Decimal("100"))
            entry.unit_price = round(entry.unit_price * multiplier, 2)
            entry.save(update_fields=["unit_price", "updated_at"])
            count += 1

        logger.info(
            f"Bulk price update on price book {price_book_id}: "
            f"{count} entries adjusted by {adjustment_percent}%"
        )
        return count

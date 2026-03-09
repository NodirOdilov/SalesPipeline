"""
Tests for the products app: models, serializers, views, and services.
"""

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import PriceBook, PriceBookEntry, Product, ProductCategory
from .services import ProductService

User = get_user_model()


class ProductCategoryModelTest(TestCase):
    """Tests for ProductCategory model."""

    def setUp(self):
        self.parent = ProductCategory.objects.create(
            name="Software", slug="software", sort_order=1
        )
        self.child = ProductCategory.objects.create(
            name="CRM", slug="crm", parent=self.parent, sort_order=1
        )

    def test_str_representation(self):
        self.assertEqual(str(self.parent), "Software")

    def test_full_path(self):
        self.assertEqual(self.child.full_path, "Software > CRM")

    def test_product_count_empty(self):
        self.assertEqual(self.parent.product_count, 0)


class ProductModelTest(TestCase):
    """Tests for Product model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="sales@example.com",
            password="testpass123!",
            first_name="Sales",
            last_name="Rep",
        )
        self.product = Product.objects.create(
            name="Enterprise CRM License",
            sku="CRM-ENT-001",
            unit_price=Decimal("299.99"),
            cost_price=Decimal("50.00"),
            product_type=Product.ProductType.SUBSCRIPTION,
            billing_frequency=Product.BillingFrequency.MONTHLY,
            created_by=self.user,
        )

    def test_str_representation(self):
        self.assertEqual(str(self.product), "Enterprise CRM License (CRM-ENT-001)")

    def test_margin_calculation(self):
        expected_margin = round((299.99 - 50.00) / 299.99 * 100, 2)
        self.assertEqual(self.product.margin, expected_margin)

    def test_margin_zero_cost(self):
        self.product.cost_price = Decimal("0")
        self.product.save()
        self.assertEqual(self.product.margin, 100.0)

    def test_is_low_stock_false_when_not_tracked(self):
        self.assertFalse(self.product.is_low_stock)

    def test_is_low_stock_true_when_tracked_and_low(self):
        self.product.track_inventory = True
        self.product.stock_quantity = 3
        self.product.save()
        self.assertTrue(self.product.is_low_stock)


class PriceBookModelTest(TestCase):
    """Tests for PriceBook model."""

    def setUp(self):
        self.book = PriceBook.objects.create(
            name="Standard Pricing", is_default=True
        )

    def test_str_representation(self):
        self.assertEqual(str(self.book), "Standard Pricing")

    def test_only_one_default(self):
        new_book = PriceBook.objects.create(name="Premium Pricing", is_default=True)
        self.book.refresh_from_db()
        self.assertFalse(self.book.is_default)
        self.assertTrue(new_book.is_default)


class ProductServiceTest(TestCase):
    """Tests for ProductService."""

    def setUp(self):
        self.service = ProductService()
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123!",
            first_name="Admin",
            last_name="User",
        )
        self.product = Product.objects.create(
            name="Basic Plan",
            sku="PLAN-BASIC",
            unit_price=Decimal("99.00"),
            cost_price=Decimal("10.00"),
            track_inventory=True,
            stock_quantity=100,
            created_by=self.user,
        )
        self.price_book = PriceBook.objects.create(
            name="Partner Pricing",
            is_default=True,
            is_active=True,
            created_by=self.user,
        )
        self.entry = PriceBookEntry.objects.create(
            price_book=self.price_book,
            product=self.product,
            unit_price=Decimal("79.00"),
            minimum_quantity=1,
            discount_percent=Decimal("10.00"),
        )

    def test_resolve_price_from_price_book(self):
        result = self.service.resolve_price(
            str(self.product.id), quantity=5, price_book_id=str(self.price_book.id)
        )
        self.assertEqual(result["price_source"], "price_book")
        # 79.00 - 10% = 71.10
        self.assertAlmostEqual(result["unit_price"], 71.10, places=2)

    def test_resolve_price_fallback_to_list(self):
        self.entry.is_active = False
        self.entry.save()
        result = self.service.resolve_price(
            str(self.product.id), quantity=1
        )
        self.assertEqual(result["price_source"], "list_price")
        self.assertEqual(result["unit_price"], 99.00)

    def test_check_inventory_available(self):
        result = self.service.check_inventory(str(self.product.id), 50)
        self.assertTrue(result["available"])
        self.assertEqual(result["remaining_after"], 50)

    def test_check_inventory_unavailable(self):
        result = self.service.check_inventory(str(self.product.id), 200)
        self.assertFalse(result["available"])

    def test_adjust_stock(self):
        updated = self.service.adjust_stock(str(self.product.id), -10, "sale")
        self.assertEqual(updated.stock_quantity, 90)

    def test_adjust_stock_insufficient(self):
        with self.assertRaises(ValueError):
            self.service.adjust_stock(str(self.product.id), -200, "oversell")


class ProductAPITest(TestCase):
    """Tests for product API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="testpass123!",
            first_name="Admin",
            last_name="User",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin)
        self.category = ProductCategory.objects.create(
            name="SaaS", slug="saas"
        )
        self.product = Product.objects.create(
            name="Pro Plan",
            sku="PLAN-PRO",
            unit_price=Decimal("199.00"),
            category=self.category,
            created_by=self.admin,
        )

    def test_list_products(self):
        url = reverse("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product(self):
        url = reverse("product-list")
        data = {
            "name": "Enterprise Plan",
            "sku": "PLAN-ENT",
            "unit_price": "499.00",
            "product_type": "subscription",
            "billing_frequency": "annual",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(sku="PLAN-ENT").exists())

    def test_retrieve_product(self):
        url = reverse("product-detail", args=[str(self.product.id)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["sku"], "PLAN-PRO")

    def test_category_tree(self):
        url = reverse("product-category-tree")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

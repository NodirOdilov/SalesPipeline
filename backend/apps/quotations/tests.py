"""
Tests for the quotations app: models, serializers, views, and services.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.products.models import Product

from .models import Quotation, QuotationLineItem, QuotationTemplate
from .services import QuotationService

User = get_user_model()


class QuotationTemplateModelTest(TestCase):
    """Tests for QuotationTemplate model."""

    def test_only_one_default(self):
        t1 = QuotationTemplate.objects.create(name="Template A", is_default=True)
        t2 = QuotationTemplate.objects.create(name="Template B", is_default=True)
        t1.refresh_from_db()
        self.assertFalse(t1.is_default)
        self.assertTrue(t2.is_default)

    def test_str_representation(self):
        t = QuotationTemplate.objects.create(name="Standard Quote")
        self.assertEqual(str(t), "Standard Quote")


class QuotationModelTest(TestCase):
    """Tests for Quotation model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="rep@example.com",
            password="testpass123!",
            first_name="Sales",
            last_name="Rep",
        )
        self.quotation = Quotation.objects.create(
            quote_number="QT-202603-0001",
            title="Enterprise Proposal",
            customer_name="Acme Corp",
            customer_email="buyer@acme.com",
            prepared_by=self.user,
            valid_until=timezone.now().date(),
        )

    def test_str_representation(self):
        self.assertIn("QT-202603-0001", str(self.quotation))

    def test_is_expired_false(self):
        self.quotation.valid_until = timezone.now().date() + timezone.timedelta(days=30)
        self.assertFalse(self.quotation.is_expired)

    def test_is_expired_true(self):
        self.quotation.valid_until = timezone.now().date() - timezone.timedelta(days=1)
        self.assertTrue(self.quotation.is_expired)

    def test_line_item_count(self):
        self.assertEqual(self.quotation.line_item_count, 0)


class QuotationLineItemModelTest(TestCase):
    """Tests for QuotationLineItem model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="rep@example.com",
            password="testpass123!",
            first_name="Sales",
            last_name="Rep",
        )
        self.quotation = Quotation.objects.create(
            quote_number="QT-202603-0002",
            title="Test Quote",
            customer_name="Test Co",
            customer_email="test@test.com",
            prepared_by=self.user,
        )
        self.item = QuotationLineItem.objects.create(
            quotation=self.quotation,
            description="CRM License",
            quantity=Decimal("10"),
            unit_price=Decimal("100.00"),
            discount_percent=Decimal("10"),
            tax_rate=Decimal("8"),
        )

    def test_line_total(self):
        self.assertEqual(self.item.line_total, Decimal("1000.00"))

    def test_discount_amount(self):
        self.assertEqual(self.item.discount_amount, Decimal("100.00"))

    def test_net_total(self):
        self.assertEqual(self.item.net_total, Decimal("900.00"))

    def test_tax_amount(self):
        self.assertEqual(self.item.tax_amount, Decimal("72.00"))

    def test_total(self):
        self.assertEqual(self.item.total, Decimal("972.00"))


class QuotationServiceTest(TestCase):
    """Tests for QuotationService."""

    def setUp(self):
        self.service = QuotationService()
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="testpass123!",
            first_name="Admin",
            last_name="User",
            role="admin",
        )
        self.quotation = Quotation.objects.create(
            quote_number="QT-202603-0003",
            title="Test Quote",
            customer_name="Test Co",
            customer_email="test@test.com",
            prepared_by=self.user,
            subtotal=Decimal("1000"),
            total_amount=Decimal("1000"),
        )
        QuotationLineItem.objects.create(
            quotation=self.quotation,
            description="Item 1",
            quantity=Decimal("5"),
            unit_price=Decimal("200.00"),
        )

    def test_create_revision(self):
        revised = self.service.create_revision(self.quotation, self.user)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, Quotation.Status.REVISED)
        self.assertEqual(revised.version, 2)
        self.assertEqual(revised.parent_quotation, self.quotation)
        self.assertEqual(revised.line_items.count(), 1)

    def test_recalculate_totals(self):
        self.service.recalculate_totals(self.quotation)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.subtotal, Decimal("1000.00"))
        self.assertEqual(self.quotation.total_amount, Decimal("1000.00"))

    def test_expire_overdue_quotations(self):
        self.quotation.status = Quotation.Status.SENT
        self.quotation.valid_until = timezone.now().date() - timezone.timedelta(days=5)
        self.quotation.save()
        count = self.service.expire_overdue_quotations()
        self.assertEqual(count, 1)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, Quotation.Status.EXPIRED)

    def test_conversion_rate(self):
        result = self.service.calculate_conversion_rate()
        self.assertIn("conversion_rate", result)
        self.assertIn("total", result)


class QuotationAPITest(TestCase):
    """Tests for quotation API endpoints."""

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
        self.quotation = Quotation.objects.create(
            quote_number="QT-202603-0010",
            title="API Test Quote",
            customer_name="API Client",
            customer_email="api@test.com",
            prepared_by=self.admin,
        )

    def test_list_quotations(self):
        url = reverse("quotation-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_quotation(self):
        url = reverse("quotation-list")
        data = {
            "title": "New Proposal",
            "customer_name": "New Client",
            "customer_email": "new@client.com",
            "line_items": [
                {
                    "description": "Consulting",
                    "quantity": "10",
                    "unit_price": "150.00",
                }
            ],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_send_quotation(self):
        url = reverse("quotation-send", args=[str(self.quotation.id)])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quotation.refresh_from_db()
        self.assertEqual(self.quotation.status, Quotation.Status.SENT)

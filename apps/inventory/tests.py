from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from services.predictions import predict_product_stock, top_risk_predictions

from .models import Category, Product


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")

    def test_stock_status_low_when_below_threshold(self):
        product = Product.objects.create(
            name="Router",
            sku="SN-TEST-1",
            category=self.category,
            price=25,
            stock=4,
            low_stock_threshold=5,
        )
        self.assertEqual(product.stock_status, Product.StockStatus.LOW)

    def test_stock_status_out_when_zero(self):
        product = Product.objects.create(
            name="Switch",
            sku="SN-TEST-2",
            category=self.category,
            price=55,
            stock=0,
            low_stock_threshold=5,
        )
        self.assertEqual(product.stock_status, Product.StockStatus.OUT)


class ProductViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewer", password="Viewer123!")
        self.category = Category.objects.create(name="Hardware")
        Product.objects.create(
            name="Keyboard",
            sku="SN-TEST-3",
            category=self.category,
            price=10,
            stock=20,
        )

    def test_product_page_requires_login(self):
        response = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(response.status_code, 302)

    def test_product_page_loads_for_authenticated_user_with_permission(self):
        permission = Permission.objects.get(codename="view_product")
        self.user.user_permissions.add(permission)
        self.client.login(username="viewer", password="Viewer123!")
        response = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(response.status_code, 200)


class PredictionServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Accessories")

    def test_prediction_payload_has_expected_fields(self):
        product = Product.objects.create(
            name="Webcam",
            sku="SN-PRED-1",
            category=self.category,
            price=70,
            stock=12,
            low_stock_threshold=5,
        )
        result = predict_product_stock(product)

        self.assertIn("risk_level", result)
        self.assertIn("recommended_reorder", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["product_id"], product.id)

    def test_top_risk_predictions_excludes_low_risk_by_default(self):
        p1 = Product.objects.create(
            name="Critical SKU",
            sku="SN-PRED-2",
            category=self.category,
            price=70,
            stock=1,
            low_stock_threshold=10,
        )
        Product.objects.create(
            name="Safe SKU",
            sku="SN-PRED-3",
            category=self.category,
            price=70,
            stock=500,
            low_stock_threshold=10,
        )

        rows = top_risk_predictions(limit=10)
        self.assertTrue(any(r["product_id"] == p1.id for r in rows))
        self.assertTrue(all(r["risk_level"] in {"high", "medium"} for r in rows))

# Create your tests here.


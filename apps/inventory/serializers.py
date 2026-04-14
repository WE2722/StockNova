from rest_framework import serializers

from .models import Category, Product, StockMovement


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "category",
            "category_id",
            "price",
            "stock",
            "low_stock_threshold",
            "stock_status",
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    performed_by_username = serializers.CharField(source="performed_by.username", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "movement_type",
            "quantity",
            "previous_stock",
            "new_stock",
            "note",
            "performed_by",
            "performed_by_username",
            "created_at",
        ]


class ProductPredictionSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    sku = serializers.CharField()
    name = serializers.CharField()
    current_stock = serializers.IntegerField()
    avg_daily_consumption = serializers.FloatField()
    days_to_stockout = serializers.FloatField(allow_null=True)
    risk_level = serializers.CharField()
    recommended_reorder = serializers.IntegerField()
    confidence = serializers.FloatField()
    urgency_score = serializers.FloatField()

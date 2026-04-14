from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import filters, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from services.predictions import predict_product_stock, top_risk_predictions

from .models import Category, Product, StockMovement
from .serializers import (
    CategorySerializer,
    ProductPredictionSerializer,
    ProductSerializer,
    StockMovementSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "category__name"]
    ordering_fields = ["name", "price", "stock", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        category_id = self.request.query_params.get("category_id")
        stock_status = self.request.query_params.get("stock_status")
        if category_id:
            qs = qs.filter(category_id=category_id)
        if stock_status:
            qs = qs.filter(stock_status=stock_status)
        return qs


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("product", "performed_by").all()
    serializer_class = StockMovementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "quantity"]

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get("product_id")
        movement_type = self.request.query_params.get("movement_type")
        if product_id:
            qs = qs.filter(product_id=product_id)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        return qs


class DashboardStatsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        products = Product.objects.all()
        payload = {
            "total_products": products.count(),
            "total_categories": Category.objects.count(),
            "low_stock": products.filter(stock_status=Product.StockStatus.LOW).count(),
            "out_of_stock": products.filter(stock_status=Product.StockStatus.OUT).count(),
            "category_breakdown": list(
                Category.objects.annotate(product_count=Count("products")).values("name", "product_count")
            ),
        }
        return Response(payload)


class ProductPredictionListApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        horizon_days = float(request.query_params.get("horizon_days", 21))
        include_low_risk = request.query_params.get("include_low_risk", "false").lower() == "true"

        data = top_risk_predictions(
            limit=limit,
            horizon_days=horizon_days,
            include_low_risk=include_low_risk,
        )
        serializer = ProductPredictionSerializer(data, many=True)
        return Response(serializer.data)


class ProductPredictionApiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id: int):
        product = get_object_or_404(Product, pk=product_id)
        serializer = ProductPredictionSerializer(predict_product_stock(product))
        return Response(serializer.data)

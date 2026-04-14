from django.urls import path
from rest_framework.routers import DefaultRouter

from .api import (
    CategoryViewSet,
    DashboardStatsApiView,
    ProductPredictionApiView,
    ProductPredictionListApiView,
    ProductViewSet,
    StockMovementViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("products", ProductViewSet)
router.register("stock-movements", StockMovementViewSet)

urlpatterns = router.urls + [
    path("dashboard/stats/", DashboardStatsApiView.as_view(), name="api_dashboard_stats"),
    path("predictions/", ProductPredictionListApiView.as_view(), name="api_prediction_list"),
    path("predictions/<int:product_id>/", ProductPredictionApiView.as_view(), name="api_prediction_detail"),
]

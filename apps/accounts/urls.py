from django.urls import path

from .views import StockNovaLoginView, StockNovaLogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", StockNovaLoginView.as_view(), name="login"),
    path("logout/", StockNovaLogoutView.as_view(), name="logout"),
]

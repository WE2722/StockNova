from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.home_redirect, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/predictions/live/", views.live_predictions_widget, name="live_predictions_widget"),
    path("predictions/", views.prediction_dashboard, name="prediction_dashboard"),
    path("predictions/live/", views.prediction_dashboard_live, name="prediction_dashboard_live"),
    path("products/", views.product_list, name="product_list"),
    path("products/create/", views.product_create, name="product_create"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/edit/", views.product_update, name="product_update"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("products/<int:pk>/stock/<str:action>/", views.adjust_stock, name="adjust_stock"),
    path("products/export/csv/", views.export_products_csv, name="export_products_csv"),
    path("products/export/excel/", views.export_products_excel, name="export_products_excel"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("audit-logs/", views.audit_log_list, name="audit_log_list"),
]

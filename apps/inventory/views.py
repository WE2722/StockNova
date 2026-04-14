import csv
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from services.audit import log_action
from services.predictions import top_risk_predictions

from .forms import CategoryForm, ProductForm, StockAdjustForm
from .models import AuditLog, Category, Product, StockMovement
from .tasks import notify_low_stock_products


def _product_queryset(request):
    qs = Product.objects.select_related("category").all()

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    stock_status = request.GET.get("stock_status", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "name")

    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    if category:
        qs = qs.filter(category_id=category)
    if stock_status:
        qs = qs.filter(stock_status=stock_status)
    if min_price:
        qs = qs.filter(price__gte=Decimal(min_price))
    if max_price:
        qs = qs.filter(price__lte=Decimal(max_price))

    allowed_sort = {
        "name": "name",
        "-name": "-name",
        "price": "price",
        "-price": "-price",
        "stock": "stock",
        "-stock": "-stock",
        "created": "-created_at",
    }
    qs = qs.order_by(allowed_sort.get(sort, "name"))
    return qs


@login_required
def dashboard(request):
    products = Product.objects.all()
    categories_count = Category.objects.count()
    total_products = products.count()
    low_stock = products.filter(stock_status=Product.StockStatus.LOW).count()
    out_of_stock = products.filter(stock_status=Product.StockStatus.OUT).count()

    category_breakdown = (
        Category.objects.annotate(product_count=Count("products"))
        .values("name", "product_count")
        .order_by("name")
    )
    prediction_rows = top_risk_predictions(limit=8, horizon_days=21, include_low_risk=False)
    predicted_stockout_7d = sum(
        1
        for item in prediction_rows
        if item["days_to_stockout"] is not None and item["days_to_stockout"] <= 7
    )

    context = {
        "total_products": total_products,
        "categories_count": categories_count,
        "low_stock": low_stock,
        "out_of_stock": out_of_stock,
        "predicted_stockout_7d": predicted_stockout_7d,
        "prediction_rows": prediction_rows,
        "prediction_generated_at": timezone.localtime(),
        "chart_labels": json.dumps([c["name"] for c in category_breakdown]),
        "chart_data": json.dumps([c["product_count"] for c in category_breakdown]),
        "recent_movements": StockMovement.objects.select_related("product", "performed_by")[:8],
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def live_predictions_widget(request):
    context = {
        "prediction_rows": top_risk_predictions(limit=12, horizon_days=30, include_low_risk=False),
        "prediction_generated_at": timezone.localtime(),
    }
    return render(request, "inventory/partials/prediction_table.html", context)


@login_required
def prediction_dashboard(request):
    predictions = top_risk_predictions(limit=50, horizon_days=30, include_low_risk=True)

    high = sum(1 for p in predictions if p["risk_level"] == "high")
    medium = sum(1 for p in predictions if p["risk_level"] == "medium")
    low = sum(1 for p in predictions if p["risk_level"] == "low")
    soon_7d = sum(1 for p in predictions if p["days_to_stockout"] is not None and p["days_to_stockout"] <= 7)

    top_urgent = sorted(predictions, key=lambda p: -p.get("urgency_score", 0))[:10]

    context = {
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "soon_7d": soon_7d,
        "risk_labels": json.dumps(["High", "Medium", "Low"]),
        "risk_data": json.dumps([high, medium, low]),
        "urgent_labels": json.dumps([p["sku"] for p in top_urgent]),
        "urgent_days": json.dumps([p["days_to_stockout"] if p["days_to_stockout"] is not None else 999 for p in top_urgent]),
        "prediction_rows": top_risk_predictions(limit=20, horizon_days=30, include_low_risk=False),
        "prediction_generated_at": timezone.localtime(),
    }
    return render(request, "inventory/prediction_dashboard.html", context)


@login_required
def prediction_dashboard_live(request):
    context = {
        "prediction_rows": top_risk_predictions(limit=20, horizon_days=30, include_low_risk=False),
        "prediction_generated_at": timezone.localtime(),
    }
    return render(request, "inventory/partials/prediction_table.html", context)


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def product_list(request):
    products = _product_queryset(request)
    paginator = Paginator(products, 10)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "products": page,
        "categories": Category.objects.all(),
        "stock_choices": Product.StockStatus.choices,
        "low_alert_count": Product.objects.filter(stock_status=Product.StockStatus.LOW).count(),
        "out_alert_count": Product.objects.filter(stock_status=Product.StockStatus.OUT).count(),
    }

    if request.htmx:
        return render(request, "inventory/partials/product_table.html", context)
    return render(request, "inventory/product_list.html", context)


@login_required
@permission_required("inventory.add_product", raise_exception=True)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        log_action(actor=request.user, action="PRODUCT_CREATED", obj=product)
        if product.stock_status in [Product.StockStatus.LOW, Product.StockStatus.OUT]:
            notify_low_stock_products.delay([product.id])
        messages.success(request, "Product created successfully.")
        return redirect("inventory:product_list")
    return render(request, "inventory/product_form.html", {"form": form, "title": "Create product"})


@login_required
@permission_required("inventory.change_product", raise_exception=True)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        product = form.save()
        log_action(actor=request.user, action="PRODUCT_UPDATED", obj=product)
        if product.stock_status in [Product.StockStatus.LOW, Product.StockStatus.OUT]:
            notify_low_stock_products.delay([product.id])
        messages.success(request, "Product updated successfully.")
        return redirect("inventory:product_list")
    return render(request, "inventory/product_form.html", {"form": form, "title": "Update product"})


@login_required
@permission_required("inventory.delete_product", raise_exception=True)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        log_action(actor=request.user, action="PRODUCT_DELETED", obj=product)
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect("inventory:product_list")
    return render(request, "inventory/confirm_delete.html", {"object": product, "type": "product"})


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    movements = product.movements.select_related("performed_by")[:20]
    return render(
        request,
        "inventory/product_detail.html",
        {"product": product, "movements": movements},
    )


@login_required
@permission_required("inventory.change_product", raise_exception=True)
def adjust_stock(request, pk, action):
    product = get_object_or_404(Product, pk=pk)
    form = StockAdjustForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        qty = form.cleaned_data["quantity"]
        note = form.cleaned_data["note"]
        previous_stock = product.stock

        if action == "decrease" and qty > product.stock:
            messages.error(request, "Cannot decrease more than current stock.")
            return redirect("inventory:product_detail", pk=product.pk)

        if action == "increase":
            product.stock += qty
            movement_type = StockMovement.MovementType.INCREASE
        else:
            product.stock -= qty
            movement_type = StockMovement.MovementType.DECREASE

        product.save()
        StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=qty,
            previous_stock=previous_stock,
            new_stock=product.stock,
            note=note,
            performed_by=request.user,
        )
        log_action(
            actor=request.user,
            action=f"STOCK_{action.upper()}",
            obj=product,
            metadata={"quantity": qty, "from": previous_stock, "to": product.stock},
        )
        if product.stock_status in [Product.StockStatus.LOW, Product.StockStatus.OUT]:
            notify_low_stock_products.delay([product.id])
        messages.success(request, "Stock updated successfully.")
        return redirect("inventory:product_detail", pk=product.pk)

    return render(
        request,
        "inventory/stock_adjust.html",
        {"form": form, "product": product, "action": action},
    )


@login_required
@permission_required("inventory.view_category", raise_exception=True)
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    return render(request, "inventory/category_list.html", {"categories": categories})


@login_required
@permission_required("inventory.add_category", raise_exception=True)
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        log_action(actor=request.user, action="CATEGORY_CREATED", obj=category)
        messages.success(request, "Category created successfully.")
        return redirect("inventory:category_list")
    return render(request, "inventory/category_form.html", {"form": form, "title": "Create category"})


@login_required
@permission_required("inventory.change_category", raise_exception=True)
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        log_action(actor=request.user, action="CATEGORY_UPDATED", obj=category)
        messages.success(request, "Category updated successfully.")
        return redirect("inventory:category_list")
    return render(request, "inventory/category_form.html", {"form": form, "title": "Update category"})


@login_required
@permission_required("inventory.delete_category", raise_exception=True)
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        log_action(actor=request.user, action="CATEGORY_DELETED", obj=category)
        category.delete()
        messages.success(request, "Category deleted.")
        return redirect("inventory:category_list")
    return render(request, "inventory/confirm_delete.html", {"object": category, "type": "category"})


@login_required
@permission_required("inventory.view_auditlog", raise_exception=True)
def audit_log_list(request):
    logs = AuditLog.objects.select_related("actor")[:100]
    return render(request, "inventory/audit_log_list.html", {"logs": logs})


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def export_products_csv(request):
    products = _product_queryset(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products_export.csv"'

    writer = csv.writer(response)
    writer.writerow(["Name", "SKU", "Category", "Price", "Stock", "Status"])
    for p in products:
        writer.writerow([p.name, p.sku, p.category.name, p.price, p.stock, p.get_stock_status_display()])
    return response


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def export_products_excel(request):
    products = _product_queryset(request)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Products"
    sheet.append(["Name", "SKU", "Category", "Price", "Stock", "Status"])
    for p in products:
        sheet.append([p.name, p.sku, p.category.name, float(p.price), p.stock, p.get_stock_status_display()])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="products_export.xlsx"'
    workbook.save(response)
    return response


@login_required
def home_redirect(request):
    return redirect(reverse("inventory:dashboard"))


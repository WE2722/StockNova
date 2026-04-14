from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from apps.inventory.models import Product


def notify_low_stock(*, product_ids=None):
    queryset = Product.objects.select_related("category").filter(
        stock_status__in=[Product.StockStatus.LOW, Product.StockStatus.OUT]
    )
    if product_ids:
        queryset = queryset.filter(id__in=product_ids)

    products = list(queryset)
    if not products:
        return 0

    User = get_user_model()
    recipients = list(
        User.objects.filter(is_active=True, is_staff=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        return 0

    lines = ["Low-stock / out-of-stock alert from StockNova AI", ""]
    for product in products:
        lines.append(
            f"- {product.name} ({product.sku}) | status={product.get_stock_status_display()} | stock={product.stock}"
        )
    send_mail(
        subject="[StockNova AI] Low stock alert",
        message="\n".join(lines),
        from_email=None,
        recipient_list=recipients,
        fail_silently=False,
    )
    return len(products)

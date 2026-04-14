from celery import shared_task

from services.notifications import notify_low_stock


@shared_task(name="apps.inventory.tasks.notify_low_stock_products")
def notify_low_stock_products(product_ids=None):
    return notify_low_stock(product_ids=product_ids)

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    class StockStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        LOW = "low", "Low stock"
        OUT = "out", "Out of stock"

    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=64, unique=True)
    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.PROTECT,
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/%Y/%m", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    stock_status = models.CharField(
        max_length=16,
        choices=StockStatus.choices,
        default=StockStatus.AVAILABLE,
        db_index=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["price"]),
            models.Index(fields=["stock_status"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def calculate_stock_status(self):
        if self.stock == 0:
            return self.StockStatus.OUT
        if self.stock <= self.low_stock_threshold:
            return self.StockStatus.LOW
        return self.StockStatus.AVAILABLE

    def save(self, *args, **kwargs):
        self.stock_status = self.calculate_stock_status()
        super().save(*args, **kwargs)


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        INCREASE = "increase", "Increase"
        DECREASE = "decrease", "Decrease"

    product = models.ForeignKey(Product, related_name="movements", on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="stock_movements",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} {self.movement_type} {self.quantity}"


class AuditLog(models.Model):
    action = models.CharField(max_length=120)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="audit_logs",
        null=True,
        on_delete=models.SET_NULL,
    )
    content_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor} on {self.object_repr}"


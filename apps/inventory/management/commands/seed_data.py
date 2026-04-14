import random
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from PIL import Image, ImageDraw

from apps.inventory.models import Category, Product


class Command(BaseCommand):
    help = "Seed realistic users, categories, and products for StockNova AI"

    def add_arguments(self, parser):
        parser.add_argument("--categories", type=int, default=8)
        parser.add_argument("--products", type=int, default=60)

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker()

        self._create_roles()
        self._create_users()

        categories = self._create_categories(fake, options["categories"])
        self._create_products(fake, categories, options["products"])

        self.stdout.write(self.style.SUCCESS("Seed completed successfully."))

    def _create_roles(self):
        superadmin_group, _ = Group.objects.get_or_create(name="Superadmin")
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        viewer_group, _ = Group.objects.get_or_create(name="Viewer")

        inventory_perms = Permission.objects.filter(content_type__app_label="inventory")
        product_perms = inventory_perms.filter(content_type__model="product")
        view_perms = inventory_perms.filter(codename__startswith="view_")

        superadmin_group.permissions.set(inventory_perms)
        admin_group.permissions.set(product_perms)
        viewer_group.permissions.set(view_perms)

    def _create_users(self):
        users = [
            ("superadmin", "Superadmin123!", "Superadmin", True, True),
            ("admin", "Admin123!", "Admin", True, False),
            ("viewer", "Viewer123!", "Viewer", False, False),
        ]
        for username, password, group_name, is_staff, is_superuser in users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": is_staff, "is_superuser": is_superuser},
            )
            if created:
                user.set_password(password)
                user.email = f"{username}@stocknova.local"
                user.save()
            group = Group.objects.get(name=group_name)
            user.groups.add(group)

    def _create_categories(self, fake, count):
        categories = []
        for _ in range(count):
            category, _ = Category.objects.get_or_create(
                name=fake.unique.word().title(),
                defaults={"description": fake.sentence(nb_words=12)},
            )
            categories.append(category)
        return categories

    def _generate_seed_image(self, sku):
        media_dir = Path(settings.MEDIA_ROOT) / "products" / "seed"
        media_dir.mkdir(parents=True, exist_ok=True)
        path = media_dir / f"{sku}.png"
        if not path.exists():
            image = Image.new("RGB", (480, 320), color=(8, 99, 117))
            draw = ImageDraw.Draw(image)
            draw.text((20, 130), f"StockNova {sku}", fill=(255, 255, 255))
            image.save(path)
        return f"products/seed/{sku}.png"

    def _create_products(self, fake, categories, count):
        for idx in range(count):
            sku = f"SN-{1000 + idx}"
            Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name": fake.unique.catch_phrase(),
                    "category": random.choice(categories),
                    "description": fake.text(max_nb_chars=180),
                    "price": Decimal(random.randint(5, 9999)) / Decimal("1.00"),
                    "stock": random.randint(0, 180),
                    "low_stock_threshold": random.choice([5, 10, 15, 20]),
                    "image": self._generate_seed_image(sku),
                },
            )

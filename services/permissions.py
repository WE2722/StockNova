from django.contrib.auth.decorators import permission_required

superadmin_required = permission_required("auth.view_user", raise_exception=True)
can_manage_products = permission_required("inventory.change_product", raise_exception=True)
can_manage_categories = permission_required("inventory.change_category", raise_exception=True)

from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "image":
                field.widget.attrs.setdefault("class", "form-control")
            elif name == "category":
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

    class Meta:
        model = Product
        fields = [
            "name",
            "sku",
            "category",
            "description",
            "image",
            "price",
            "stock",
            "low_stock_threshold",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class StockAdjustForm(forms.Form):
    quantity = forms.IntegerField(min_value=1)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quantity"].widget.attrs.setdefault("class", "form-control")
        self.fields["note"].widget.attrs.setdefault("class", "form-control")

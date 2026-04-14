from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import LoginForm, SignUpForm


class LandingPageView(TemplateView):
    template_name = "accounts/landing.html"


class SignUpView(FormView):
    template_name = "accounts/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("inventory:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("inventory:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        viewer_group, _ = Group.objects.get_or_create(name="Viewer")
        user.groups.add(viewer_group)
        login(self.request, user)
        messages.success(self.request, "Welcome to StockNova AI.")
        return redirect(reverse("inventory:dashboard"))


class StockNovaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class StockNovaLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


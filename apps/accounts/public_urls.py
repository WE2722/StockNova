from django.urls import path

from .views import LandingPageView, SignUpView

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("signup/", SignUpView.as_view(), name="signup"),
]

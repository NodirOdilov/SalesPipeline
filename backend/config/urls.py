"""
URL configuration for SalesPipeline project.
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT Authentication
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # App URLs
    path("api/auth/", include("apps.accounts.urls")),
    path("api/leads/", include("apps.leads.urls")),
    path("api/pipeline/", include("apps.pipeline.urls")),
    path("api/forecasting/", include("apps.forecasting.urls")),
    path("api/sequences/", include("apps.sequences.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
]

"""
Development-specific Django settings.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Enable browsable API in development
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# Ensure logs directory exists
import os

LOGS_DIR = BASE_DIR / "logs"  # noqa: F405
os.makedirs(LOGS_DIR, exist_ok=True)

# Additional development apps
try:
    import django_extensions  # noqa: F401
    INSTALLED_APPS += ["django_extensions"]  # noqa: F405
except ImportError:
    pass

from .base import *
import os

DEBUG = False
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 600,
    }
}

# Cache — Redis
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Security headers (расширить при настройке HTTPS в Part 2)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# django-axes
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
AXES_CACHE = "default"

# Wagtail search
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# try:
#     from .local import *
# except ImportError:
#     pass

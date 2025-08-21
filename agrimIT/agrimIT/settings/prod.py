"""
Production settings for agrimIT project.
These settings are used in production environment.
"""

import os
from .base import *
import dj_database_url

# Override critical settings for production
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')

# Validate that SECRET_KEY is provided
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in production")

# Add whitenoise middleware for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Production hosts - Railway compatible
ALLOWED_HOSTS = ['*']  # Railway handles domain routing securely

# Production database - Railway PostgreSQL
DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}
# Security settings for production - adjusted for Railway
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
# Railway handles SSL termination
SECURE_SSL_REDIRECT = False  # Railway handles this
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_TZ = True

# Session security - adjusted for Railway
SESSION_COOKIE_SECURE = False  # Railway handles SSL termination
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600

# CSRF security - adjusted for Railway
CSRF_COOKIE_SECURE = False  # Railway handles SSL termination
CSRF_COOKIE_HTTPONLY = True



# Email backend for production
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = os.environ.get('EMAIL_HOST')
#EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
#EMAIL_USE_TLS = True
#EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
#EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
#DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# Production logging - Railway compatible
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache settings for production - disable Redis for now
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

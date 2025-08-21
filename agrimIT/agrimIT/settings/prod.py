"""
Production settings for agrimIT project.
These settings are used in production environment.
"""

import os
from .base import *
import dj_database_url

# Add whitenoise middleware for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Production hosts - should be set via environment variable
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', default='localhost').split(',')

# Production database - should be set via environment variables
DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}
# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_TZ = True

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600

# CSRF security
CSRF_COOKIE_SECURE = True
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

# Cache settings for production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
    }
}

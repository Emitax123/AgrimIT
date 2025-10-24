"""
Production settings for agrimIT project.
These settings are used in production environment.
"""

import os
from .base import *
import dj_database_url

# Override critical settings for production
DEBUG = False

# Environment variables validation with detailed error messages
def get_required_env(var_name, error_msg=None):
    """Get required environment variable with validation"""
    value = os.environ.get(var_name)
    if not value:
        error_msg = error_msg or f"{var_name} environment variable is required in production"
        raise ValueError(error_msg)
    return value

def get_optional_env(var_name, default=None, cast_func=None):
    """Get optional environment variable with optional type casting"""
    value = os.environ.get(var_name, default)
    if cast_func and value is not None:
        try:
            return cast_func(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for {var_name}: {value}. Error: {e}")
    return value

# Validate required environment variables
SECRET_KEY = get_required_env('SECRET_KEY', 
    "SECRET_KEY must be set in production. Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'")

DATABASE_URL = get_required_env('DATABASE_URL',
    "DATABASE_URL is required for Railway PostgreSQL connection")

# Validate optional but recommended environment variables
SUPABASE_URL = get_optional_env('SUPABASE_URL')
SUPABASE_KEY = get_optional_env('SUPABASE_KEY')
SUPABASE_BUCKET = get_optional_env('SUPABASE_BUCKET')

# Warn if Supabase is not configured (if your app uses it)
if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET]):
    import warnings
    warnings.warn("Supabase environment variables not fully configured. File upload functionality may not work.")

# Override base.py values with validated ones
globals().update({
    'SUPABASE_URL': SUPABASE_URL,
    'SUPABASE_KEY': SUPABASE_KEY,
    'SUPABASE_BUCKET': SUPABASE_BUCKET,
})

# Add security and performance middleware for production
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Security middleware configuration - enhanced
MIDDLEWARE += [
    # Custom security middleware (will be created)
    'agrimIT.middleware.SecurityHeadersMiddleware',
    'agrimIT.middleware.RateLimitMiddleware',
]

# Templates configuration for production - SECURE (no debug context processor)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.parent / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # 'django.template.context_processors.debug',  # ❌ REMOVED for security
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Production hosts - Railway domains + healthcheck
# Get Railway domain from environment (Railway sets RAILWAY_STATIC_URL)
railway_domain = os.environ.get('RAILWAY_STATIC_URL', '').replace('https://', '').replace('http://', '')
if not railway_domain:
    railway_domain = 'agrimit-production.up.railway.app'  # Fallback to your actual domain

allowed_hosts_env = get_optional_env('DJANGO_ALLOWED_HOSTS', 
    default=f'{railway_domain},healthcheck.railway.app')

ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]

# Always include essential Railway domains
railway_domains = [
    'healthcheck.railway.app',
    railway_domain,  # Dynamic Railway domain
    'agrimit-production.up.railway.app',  # Your specific domain
    '*.railway.app',
    '*.up.railway.app'
]

for domain in railway_domains:
    if domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(domain)

# Log the allowed hosts for debugging
import logging
railway_logger = logging.getLogger(__name__)
railway_logger.info(f"Railway domain detected: {railway_domain}")
railway_logger.info(f"ALLOWED_HOSTS configured: {ALLOWED_HOSTS}")

# Production database - Railway PostgreSQL with validation
DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Validate database configuration
if not DATABASES['default'].get('NAME'):
    raise ValueError("Database configuration is invalid. Check DATABASE_URL format.")

# Security settings for production - enhanced
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_REDIRECT_EXEMPT = []

# Railway handles SSL termination but we can add some extra security
SECURE_SSL_REDIRECT = False  # Railway handles this at infrastructure level
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Additional security headers
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy (will be handled by custom middleware)
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Request size limits (10MB default)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_REQUEST_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_REQUEST_SIZE

# Admin IP whitelist (configure if needed)
# ADMIN_IP_WHITELIST = ['192.168.1.100', '10.0.0.50']  # Uncomment and configure IPs

USE_TZ = True

# Session security - secure for Railway production
SESSION_COOKIE_SECURE = True   # ✅ HTTPS only cookies (Railway forwards HTTPS properly)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 31536000  # 1 año (365 días * 24 horas * 60 minutos * 60 segundos)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # La sesión persiste aunque se cierre el navegador
SESSION_SAVE_EVERY_REQUEST = True  # Renueva la sesión en cada request
SESSION_COOKIE_SAMESITE = 'Lax'  # Protección adicional CSRF

# CSRF security - secure for Railway production
CSRF_COOKIE_SECURE = True   # ✅ HTTPS only CSRF cookies
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
# CSRF security - secure for Railway production
CSRF_COOKIE_SECURE = True   # ✅ HTTPS only CSRF cookies
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Build CSRF trusted origins dynamically
csrf_origins = [
    f'https://{railway_domain}',  # Dynamic Railway domain
    'https://agrimit-production.up.railway.app',  # Your specific domain
    'https://healthcheck.railway.app',  # Railway healthcheck
    'https://*.railway.app',  # Wildcard for Railway subdomains
]

# Add custom domain if configured
custom_domain = os.environ.get('CUSTOM_DOMAIN')
if custom_domain:
    csrf_origins.append(f'https://{custom_domain}')

CSRF_TRUSTED_ORIGINS = csrf_origins

# Log CSRF origins for debugging
railway_logger.info(f"CSRF_TRUSTED_ORIGINS configured: {CSRF_TRUSTED_ORIGINS}")



# Email backend for production
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = os.environ.get('EMAIL_HOST')
#EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
#EMAIL_USE_TLS = True
#EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
#EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
#DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

# Production logging - Railway compatible with structured logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json_formatter': {
            'format': 'LEVEL={levelname} TIME={asctime} MODULE={module} PROCESS={process} THREAD={thread} MESSAGE={message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'error_console': {
            'level': 'ERROR',
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
        'agrimIT': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.project_admin': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.accounting': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.clients': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.users': {
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

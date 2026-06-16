"""
Development settings for agrimIT project.
These settings are used during development.
"""

from .base import *

# DEBUG is inherited from base.py which reads from DJANGO_DEBUG env var
# If you want to override it specifically for development, uncomment:
# DEBUG = True

# Templates configuration for development - includes debug context processor
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR.parent / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',    # ✅ OK in development
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Hosts allowed during development
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database for development (SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development-specific apps
INSTALLED_APPS += [
    # Add development tools here
    # 'debug_toolbar',
    # 'django_extensions',
]

# Development-specific middleware
MIDDLEWARE += [
    # Add development middleware here
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Email backend for development (console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files settings for development
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Development logging with structured format
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json_dev': {
            'format': 'LEVEL={levelname} TIME={asctime} MODULE={module} MESSAGE={message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',  # Only important messages
            'class': 'logging.handlers.RotatingFileHandler',  # Rotate logs
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'ERROR',  # Only errors in console
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file'],
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps.accounting': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',  # Less verbose in production
            'propagate': False,
        },
        'apps.project_admin': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.clients': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.users': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# ...existing code...

# Internal IPs for debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
]

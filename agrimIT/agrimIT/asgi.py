"""
ASGI config for agrimIT project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# Use the same logic as wsgi.py and manage.py
if os.environ.get('RAILWAY_ENVIRONMENT'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrimIT.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrimIT.settings.dev')

application = get_asgi_application()

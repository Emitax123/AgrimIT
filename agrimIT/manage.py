#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Load .env file first (if not in Railway)
    if not os.environ.get('RAILWAY_ENVIRONMENT'):
        from pathlib import Path
        env_file = Path(__file__).resolve().parent.parent / '.env'
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        # FORZAR el uso del .env (remover la condición)
                        os.environ[key] = value
    
    # Now decide which settings to use
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # En Railway, siempre usar producción
        os.environ['DJANGO_SETTINGS_MODULE'] = 'agrimIT.settings.prod'
    else:
        # En local, usar el valor del .env o dev como fallback
        settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'agrimIT.settings.dev')
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_module
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)



if __name__ == '__main__':
    main()

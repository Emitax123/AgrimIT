#!/usr/bin/env python
"""
Railway Domain Configuration Checker
Verifica que los dominios estén configurados correctamente
"""

import os
import sys

def check_railway_config():
    """Check Railway domain configuration"""
    
    print("🚂 RAILWAY DOMAIN CONFIGURATION CHECKER")
    print("=" * 50)
    
    # Check environment variables
    print("\n📊 ENVIRONMENT VARIABLES:")
    railway_static_url = os.environ.get('RAILWAY_STATIC_URL', 'Not set')
    custom_domain = os.environ.get('CUSTOM_DOMAIN', 'Not set')
    django_allowed_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', 'Not set')
    
    print(f"RAILWAY_STATIC_URL: {railway_static_url}")
    print(f"CUSTOM_DOMAIN: {custom_domain}")
    print(f"DJANGO_ALLOWED_HOSTS: {django_allowed_hosts}")
    
    # Determine Railway domain
    if railway_static_url != 'Not set':
        railway_domain = railway_static_url.replace('https://', '').replace('http://', '')
    else:
        railway_domain = 'agrimit-production.up.railway.app'
    
    print(f"\n🔍 DETECTED RAILWAY DOMAIN: {railway_domain}")
    
    # Expected configuration
    print("\n✅ EXPECTED ALLOWED_HOSTS:")
    expected_hosts = [
        'healthcheck.railway.app',
        railway_domain,
        'agrimit-production.up.railway.app',
        '*.railway.app',
        '*.up.railway.app'
    ]
    
    for host in expected_hosts:
        print(f"  - {host}")
    
    print("\n✅ EXPECTED CSRF_TRUSTED_ORIGINS:")
    expected_origins = [
        f'https://{railway_domain}',
        'https://agrimit-production.up.railway.app',
        'https://healthcheck.railway.app',
        'https://*.railway.app'
    ]
    
    if custom_domain != 'Not set':
        expected_origins.append(f'https://{custom_domain}')
    
    for origin in expected_origins:
        print(f"  - {origin}")
    
    print("\n🚀 DEPLOYMENT COMMANDS:")
    print("1. Set environment variable (optional):")
    print(f"   railway variables set DJANGO_ALLOWED_HOSTS='{railway_domain},healthcheck.railway.app'")
    print("\n2. Deploy:")
    print("   railway deploy")
    
    print("\n✨ Your domain should work after deployment!")
    return railway_domain

if __name__ == "__main__":
    check_railway_config()
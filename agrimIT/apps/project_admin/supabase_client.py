from supabase import create_client
import os
from django.conf import settings

# Try to get from environment variables first, then fall back to Django settings
SUPABASE_URL = os.environ.get("SUPABASE_URL") or getattr(settings, 'SUPABASE_URL', None)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or getattr(settings, 'SUPABASE_KEY', None)

if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is required. Please set it in environment variables or Django settings.")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is required. Please set it in environment variables or Django settings.")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise RuntimeError(f"Failed to initialize Supabase client: {e}")

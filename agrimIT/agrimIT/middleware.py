"""
Custom security middleware for AgrimIT project
"""

import time
from django.http import HttpResponseForbidden, HttpResponse
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def create_rate_limit_response(message="Rate limit exceeded. Please try again later.", retry_after=60):
    """Create a standardized 429 rate limit response"""
    response = HttpResponse(
        message,
        status=429,
        content_type='text/plain'
    )
    response['Retry-After'] = str(retry_after)
    return response


class SecurityHeadersMiddleware:
    """
    Adds security headers to all responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        security_headers = {
            # Prevent clickjacking
            'X-Frame-Options': 'DENY',
            
            # Prevent MIME type sniffing
            'X-Content-Type-Options': 'nosniff',
            
            # Enable XSS protection
            'X-XSS-Protection': '1; mode=block',
            
            # Referrer Policy
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # Content Security Policy (basic)
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self';"
            ),
            
            # Permissions Policy (formerly Feature Policy)
            'Permissions-Policy': (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Server header removal (security through obscurity)
            'Server': 'AgrimIT/1.0',
        }
        
        # Only add HSTS in production with HTTPS
        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            security_headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Apply headers
        for header, value in security_headers.items():
            response[header] = value
        
        # Remove server disclosure
        if 'Server' in response:
            response['Server'] = 'AgrimIT/1.0'
            
        return response


class RateLimitMiddleware:
    """
    Simple rate limiting middleware using Django cache
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rate limiting configuration
        self.RATE_LIMITS = {
            'default': {'requests': 100, 'window': 60},  # 100 requests per minute
            'auth': {'requests': 5, 'window': 60},       # 5 auth attempts per minute
            'api': {'requests': 1000, 'window': 3600},   # 1000 API calls per hour
        }

    def __call__(self, request):
        # Skip rate limiting for certain paths or in development
        if settings.DEBUG or self._should_skip_rate_limit(request):
            return self.get_response(request)
        
        # Determine rate limit type
        limit_type = self._get_limit_type(request)
        
        # Check rate limit
        if self._is_rate_limited(request, limit_type):
            logger.warning(
                f"Rate limit exceeded for IP {self._get_client_ip(request)} "
                f"on path {request.path} (type: {limit_type})"
            )
            return create_rate_limit_response()
        
        return self.get_response(request)
    
    def _should_skip_rate_limit(self, request):
        """Skip rate limiting for certain conditions"""
        skip_paths = ['/admin/', '/static/', '/media/']
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_limit_type(self, request):
        """Determine which rate limit to apply"""
        if request.path.startswith('/admin/login/') or 'login' in request.path:
            return 'auth'
        elif request.path.startswith('/api/'):
            return 'api'
        else:
            return 'default'
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        # Check for Railway/proxy headers first
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip:
            return x_real_ip
        
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _is_rate_limited(self, request, limit_type):
        """Check if request should be rate limited"""
        ip = self._get_client_ip(request)
        limits = self.RATE_LIMITS.get(limit_type, self.RATE_LIMITS['default'])
        
        # Create cache key
        cache_key = f"rate_limit:{limit_type}:{ip}"
        
        # Get current count
        current_count = cache.get(cache_key, 0)
        
        # Check limit
        if current_count >= limits['requests']:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, limits['window'])
        return False


class IPWhitelistMiddleware:
    """
    Optional IP whitelist middleware for admin access
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # IP whitelist for admin access (configure via environment)
        self.ADMIN_WHITELIST = getattr(settings, 'ADMIN_IP_WHITELIST', [])
        
        # Paths that require IP whitelist
        self.PROTECTED_PATHS = ['/admin/']

    def __call__(self, request):
        # Skip if no whitelist configured
        if not self.ADMIN_WHITELIST:
            return self.get_response(request)
        
        # Check if path requires IP whitelist
        if any(request.path.startswith(path) for path in self.PROTECTED_PATHS):
            client_ip = self._get_client_ip(request)
            
            if client_ip not in self.ADMIN_WHITELIST:
                logger.warning(
                    f"IP {client_ip} denied access to {request.path} "
                    f"(not in whitelist: {self.ADMIN_WHITELIST})"
                )
                return HttpResponseForbidden(
                    "Access denied. Your IP address is not authorized."
                )
        
        return self.get_response(request)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class RequestSizeLimitMiddleware:
    """
    Middleware to limit request body size
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Default max size: 10MB
        self.MAX_REQUEST_SIZE = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)

    def __call__(self, request):
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH')
        
        if content_length and int(content_length) > self.MAX_REQUEST_SIZE:
            logger.warning(
                f"Request size {content_length} exceeds limit {self.MAX_REQUEST_SIZE} "
                f"for path {request.path}"
            )
            return HttpResponseForbidden(
                "Request too large. Maximum size allowed is 10MB."
            )
        
        return self.get_response(request)
"""
Context processors for main app
"""
from django.utils import timezone
from datetime import timedelta


def online_status(request):
    """
    Add online status information to template context
    """
    if not request.user.is_authenticated:
        return {}
    
    # Mark user as online (last activity within last 5 minutes)
    # This is handled by middleware, but we expose it in context
    return {
        'user_is_online': request.user.is_authenticated,  # Basic check
    }

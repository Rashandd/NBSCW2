"""
Context processors for main app
"""
from django.utils import timezone
from datetime import timedelta
from .models import ServerMember


def online_status(request):
    """
    Add online status information to template context
    Provides online/offline status for users in servers
    """
    if not request.user.is_authenticated:
        return {}
    
    # Get user's online status from their server memberships
    # User is considered online if any of their memberships show them as online
    user_memberships = ServerMember.objects.filter(user=request.user)
    is_online = user_memberships.filter(is_online=True).exists() if user_memberships.exists() else True
    
    return {
        'user_is_online': is_online,
        'user_server_memberships': user_memberships if request.user.is_authenticated else None,
    }

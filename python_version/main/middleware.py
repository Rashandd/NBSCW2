"""
Middleware for tracking user online/offline status
"""
from django.utils import timezone
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from datetime import timedelta
from .models import ServerMember, CustomUser


class OnlineStatusMiddleware:
    """
    Middleware to track user online/offline status
    Updates ServerMember.is_online based on last activity
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Update user activity before processing request
        if request.user.is_authenticated:
            self.update_online_status(request.user)
        
        response = self.get_response(request)
        
        return response
    
    def update_online_status(self, user):
        """
        Update online status for user in all their server memberships
        Users are considered online if they've been active in the last 5 minutes
        """
        try:
            # Get all server memberships for this user
            server_memberships = ServerMember.objects.filter(user=user)
            
            # Mark as online (user is making requests, so they're online)
            server_memberships.update(is_online=True)
            
            # Also update last_activity if the field exists
            # This helps with more accurate offline detection
            if hasattr(user, 'last_activity'):
                user.last_activity = timezone.now()
                user.save(update_fields=['last_activity'])
            
        except Exception as e:
            # Don't break the request if there's an error
            pass
    
    @staticmethod
    def mark_users_offline():
        """
        Static method to mark users as offline if they haven't been active in 5 minutes
        This should be called periodically (e.g., via cron or celery)
        """
        try:
            five_minutes_ago = timezone.now() - timedelta(minutes=5)
            
            # If CustomUser has last_activity field, use it
            # Otherwise, we'll mark all users as potentially offline
            # and let the middleware mark them online on next request
            offline_members = ServerMember.objects.filter(
                is_online=True
            ).select_related('user')
            
            # For now, we'll keep the simple approach:
            # Users are marked online by middleware, and we rely on
            # periodic cleanup or logout signals to mark them offline
            # This is a placeholder for more sophisticated tracking
            
        except Exception as e:
            pass


@receiver(user_logged_in)
def mark_user_online(sender, request, user, **kwargs):
    """
    Mark user as online when they log in
    """
    try:
        ServerMember.objects.filter(user=user).update(is_online=True)
    except Exception:
        pass


@receiver(user_logged_out)
def mark_user_offline(sender, request, user, **kwargs):
    """
    Mark user as offline when they log out
    """
    try:
        if user and user.is_authenticated:
            ServerMember.objects.filter(user=user).update(is_online=False)
    except Exception:
        pass

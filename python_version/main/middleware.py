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
            # Update user's last activity (if you add this field to CustomUser)
            # For now, we'll update ServerMember.is_online based on activity
            
            # Get all server memberships for this user
            server_memberships = ServerMember.objects.filter(user=user)
            
            # Mark as online (we can refine this logic later)
            # For now, if user is authenticated and making requests, they're online
            server_memberships.update(is_online=True)
            
            # Note: We could implement a more sophisticated system:
            # - Store last_activity timestamp on CustomUser
            # - Check if last_activity is within last 5 minutes
            # - Set is_online accordingly
            
        except Exception as e:
            # Don't break the request if there's an error
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

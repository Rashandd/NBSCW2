"""
Management command to automatically remove game rooms that haven't been started
by the host within 1 hour.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from main.models import GameSession


class Command(BaseCommand):
    help = 'Removes game rooms that have been waiting for more than 1 hour without starting'

    def handle(self, *args, **options):
        # Find games that are waiting and created more than 1 hour ago
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        stale_games = GameSession.objects.filter(
            status='waiting',
            created_at__lt=one_hour_ago
        )
        
        count = stale_games.count()
        
        if count > 0:
            # Log before deletion
            game_ids = list(stale_games.values_list('game_id', flat=True))
            self.stdout.write(
                self.style.WARNING(
                    f'Found {count} stale game room(s) created more than 1 hour ago. Removing...'
                )
            )
            
            # Delete stale games
            stale_games.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully removed {count} stale game room(s).'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No stale game rooms found.')
            )

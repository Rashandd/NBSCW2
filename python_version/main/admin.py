# main/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.contrib.auth import get_user_model
from .models import MiniGame, GameSession, VoiceChannel

User = get_user_model()


@admin.register(MiniGame)
class MiniGameAdmin(admin.ModelAdmin):
    """
    MiniGame modeli için gelişmiş admin ayarları.
    Oyunları dinamik olarak eklemek ve yönetmek için optimize edilmiş.
    """
    list_display = ['name', 'slug', 'min_players', 'max_players', 'is_active', 'active_sessions_count', 'created_at']
    list_filter = ['is_active', 'min_players', 'max_players', 'created_at']
    search_fields = ['name', 'description', 'slug']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Oyuncu Ayarları', {
            'fields': ('min_players', 'max_players')
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        from django.db.models import Q
        qs = super().get_queryset(request)
        return qs.annotate(
            active_sessions=Count('sessions', filter=Q(sessions__status__in=['waiting', 'in_progress']))
        )
    
    def active_sessions_count(self, obj):
        """Aktif oyun sayısını gösterir"""
        if hasattr(obj, 'active_sessions'):
            return obj.active_sessions
        return obj.sessions.filter(status__in=['waiting', 'in_progress']).count()
    
    active_sessions_count.short_description = 'Aktif Oyunlar'
    active_sessions_count.admin_order_field = 'active_sessions'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    CustomUser modeli için özel admin ayarları.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'rank_point', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Oyun Bilgileri', {
            'fields': ('rank_point',)
        }),
    )
@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """
    GameSession modeli için admin ayarları.
    """
    list_display = (
        '__str__', 'game_type', 'host', 'status',
        'player_count_display', 'board_size', 'created_at'
    )
    list_filter = ('status', 'game_type', 'created_at')
    search_fields = ('game_id', 'host__username')

    readonly_fields = (
        'game_id', 'created_at', 'player_count_display', 'players_list'
    )

    fields = (
        'game_id', 'game_type', 'host', 'status', 'board_size',
        'current_turn', 'winner', 'players_list', 'board_state'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'game_type', 'host'
        ).prefetch_related('players')

    def player_count_display(self, obj):
        return f"{obj.player_count} / {obj.game_type.max_players}"

    player_count_display.short_description = "Oyuncular"

    def players_list(self, obj):
        return ", ".join([p.username for p in obj.players.all()])

    players_list.short_description = "Katılan Oyuncular"

@admin.register(VoiceChannel)
class VoiceChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_private')
    list_filter = ('is_private',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
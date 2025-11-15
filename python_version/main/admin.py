# main/admin.py

from django.contrib import admin
from django.db.models import Count
from .models import MiniGame, GameSession, VoiceChannel


@admin.register(MiniGame)
class MiniGameAdmin(admin.ModelAdmin):
    """
    MiniGame modeli için admin ayarları.
    Slug'ın otomatik dolmasını sağlar.
    """
    list_display = ['name', 'slug', 'min_players', 'max_players']
    # 'name' alanını yazarken 'slug' alanını otomatik doldur
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """
    GameSession modeli için admin ayarları.
    Daha kolay yönetim sağlar.
    """
    list_display = (
        '__str__', 'game_type', 'host', 'status',
        'player_count_display', 'board_size', 'created_at'
    )
    list_filter = ('status', 'game_type', 'created_at')
    search_fields = ('game_id', 'host__username')

    # Bu alanların admin panelinden değiştirilmesini engelle
    readonly_fields = (
        'game_id', 'created_at', 'player_count_display', 'players_list'
    )

    # Oyuncuları M2M yerine düz metin olarak göster
    fields = (
        'game_id', 'game_type', 'host', 'status', 'board_size',
        'current_turn', 'winner', 'players_list', 'board_state'
    )

    def get_queryset(self, request):
        # Performans için ilgili tabloları önden çek
        return super().get_queryset(request).select_related(
            'game_type', 'host'
        ).prefetch_related('players')

    def player_count_display(self, obj):
        # Oyuncu sayısını (N / Max) formatında göster
        return f"{obj.player_count} / {obj.game_type.max_players}"

    player_count_display.short_description = "Oyuncular"

    def players_list(self, obj):
        # Oyuncuları salt okunur bir listede göster
        return ", ".join([p.username for p in obj.players.all()])

    players_list.short_description = "Katılan Oyuncular"


@admin.register(VoiceChannel)
class VoiceChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_private')
    list_filter = ('is_private',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
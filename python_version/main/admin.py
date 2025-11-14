# main/admin.py

from django.contrib import admin
from django.db.models import Count
from .models import MiniGame, GameSession, VoiceChannel


@admin.register(MiniGame)
class MiniGameAdmin(admin.ModelAdmin):
    """
    MiniGame modeli için admin ayarları.
    """
    list_display = ['name', 'slug', 'min_players', 'max_players']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """
    GameSession modeli için admin ayarları (YENİ MODELE UYGUN).
    """
    list_display = [
        'game_id',
        'game_type',
        'host',
        'get_player_count',  # Özel fonksiyon
        'status',
        'created_at'
    ]

    list_filter = ['status', 'game_type', 'created_at']
    search_fields = [
        'game_id',
        'host__username',
        'players__username'
    ]

    def get_player_count(self, obj):
        """
        Her masadaki güncel oyuncu sayısını döndürür.
        """
        # --- DÜZELTME ---
        # 'obj.players.count()' yerine, 'get_queryset'te 'annotate'
        # ettiğimiz 'player_count_admin' değerini kullanıyoruz.
        # Bu, N+1 sorgu sorununu çözer.
        return obj.player_count_admin

    # Admin panelindeki sütun başlığı
    get_player_count.short_description = 'Oyuncu Sayısı'

    # YENİ: Sütunu sıralanabilir yapar
    get_player_count.admin_order_field = 'player_count_admin'

    # Admin listesi sorgusunu optimize etmek için
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # 'player_count_admin' adıyla bir 'Count' ekle
        qs = qs.annotate(player_count_admin=Count('players'))
        return qs


@admin.register(VoiceChannel)
class VoiceChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_private')
    list_filter = ('is_private',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
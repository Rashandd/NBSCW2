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
    # 'name' alanını doldurdukça 'slug' alanını otomatik doldurur
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """
    GameSession modeli için admin ayarları (YENİ MODELE UYGUN).
    """
    # HATA BURADAYDI: 'player1' ve 'player2' kaldırıldı.
    # 'host', 'game_type' ve özel bir 'get_player_count' fonksiyonu eklendi.
    list_display = [
        'game_id',
        'game_type',
        'host',
        'get_player_count',  # Özel fonksiyon
        'status',
        'created_at'
    ]

    list_filter = ['status', 'game_type', 'created_at']

    # HATA BURADAYDI: Aramayı 'host' ve 'players' üzerinden yap
    search_fields = [
        'game_id',
        'host__username',
        'players__username'  # M2M alanı üzerinden arama
    ]

    # 'players' bir ManyToManyField olduğu için doğrudan gösteremeyiz.
    # Bunun yerine, oyuncu sayısını gösteren bir fonksiyon yazmak daha iyidir.
    def get_player_count(self, obj):
        """
        Her masadaki güncel oyuncu sayısını döndürür.
        """
        # Modeldeki 'player_count' property'sini kullanabiliriz, 
        # ancak bu (annotate) sorgu açısından daha verimli olabilir.
        return obj.players.count()

    # Admin panelindeki sütun başlığı
    get_player_count.short_description = 'Oyuncu Sayısı'

    # Admin listesi sorgusunu optimize etmek için
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(player_count_admin=Count('players'))
        return qs


@admin.register(VoiceChannel)
class VoiceChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_private')
    list_filter = ('is_private',)
    search_fields = ('name', 'slug')

    # 'name' alanını doldururken 'slug' alanını otomatik doldurur
    prepopulated_fields = {'slug': ('name',)}
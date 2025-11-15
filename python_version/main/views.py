import json
import random

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import VoiceChannel, GameSession, default_board, MiniGame


@login_required
def index(request):
    channels = VoiceChannel.objects.all().order_by('name')

    context = {
        'channels': channels,
        'title': 'Sesli Sohbet Odaları',
    }
    return render(request, 'index.html', context)


@login_required
def voice_channel_view(request, slug):
    """Tek bir sesli sohbet odası ve chat arayüzü."""

    channel = get_object_or_404(VoiceChannel, slug=slug)

    context = {
        'channel': channel,
        'title': f'#{channel.name} Odası',
        # Kullanıcının oda slug'ını JavaScript'e aktarmak için
        'channel_slug': slug,
    }
    return render(request, 'oda.html', context)

@login_required
def settings_view(request):
    """Kullanıcının mikrofon/hoparlör seçimi yapacağı ayarlar sayfası."""
    return render(request, 'settings.html', {'title': 'Ayarlar'})

@login_required
def all_games_lobby(request):
    """
    Sistemdeki tüm 'MiniGame' türlerini listeleyen ana oyun merkezi sayfası.
    Örn: Dice Wars, Satranç, Ludo...
    """
    # Veritabanındaki tüm MiniGame nesnelerini al
    all_minigames = MiniGame.objects.all()

    context = {
        'minigames_list': all_minigames,
    }
    # minigames.html adında yeni bir template render et
    return render(request, 'minigames.html', context)


# 2. OYUNA ÖZEL LOBİ (Sorgular değişti)
@login_required
def game_specific_lobby(request, game_slug):
    game_type = get_object_or_404(MiniGame, slug=game_slug)

    # 1. Aktif Masalarım (İçinde olduğum masalar)
    my_games = GameSession.objects.filter(
        game_type=game_type,
        status__in=['waiting', 'in_progress'],
        players=request.user  # M2M sorgusu: 'players' listesinde ben var mıyım?
    ).select_related('game_type', 'host').order_by('-created_at')

    # 2. Katılınabilecek Masalar (Dolu olmayan, beklemede olan, içinde olmadığım)
    max_p = game_type.max_players
    available_games = GameSession.objects.filter(
        game_type=game_type,
        status='waiting'
    ).annotate(
        num_players=Count('players')  # Oyuncu sayısını hesapla
    ).filter(
        num_players__lt=max_p  # Dolu olmayanları filtrele
    ).exclude(
        players=request.user  # Zaten içinde olduklarımı gösterme
    ).select_related('host').order_by('-created_at')

    context = {
        'game_type': game_type,
        'my_games': my_games,
        'available_games': available_games,
    }
    return render(request, 'game_specific_lobby.html', context)


@login_required
def create_game(request, game_slug):
    game_type = get_object_or_404(MiniGame, slug=game_slug)

    # Zaten bekleyen bir odası var mı?
    if GameSession.objects.filter(game_type=game_type, host=request.user, status='waiting').exists():
        messages.warning(request, f"{game_type.name} için zaten bekleyen bir masanız var.")
        return redirect('game_specific_lobby', game_slug=game_slug)

    # --- YENİ MANTIK: Tahta Boyutunu Ayarla ---
    # Kural: 2P=5x5, 3P=6x6, 4P=7x7
    max_p = game_type.max_players

    if max_p <= 2:
        board_size = 5
    elif max_p == 3:
        board_size = 6
    else:  # 4 veya daha fazlası için
        board_size = 7
    # -----------------------------------------

    # Oda kurucuyu 'host' olarak ata ve YENİ board_size'ı kaydet
    game = GameSession.objects.create(
        game_type=game_type,
        host=request.user,
        current_turn=None,
        board_state={},
        board_size=board_size  # --- YENİ ALAN ---
    )
    # Oda kurucuyu 'players' M2M listesine ekle
    game.players.add(request.user)

    return redirect('game_room', game_id=game.game_id)


# 5. OYUN ODASI (DEĞİŞTİ)
@login_required
def game_room(request, game_id):
    game = get_object_or_404(GameSession.objects.select_related('game_type', 'host', 'current_turn', 'winner'),
                             game_id=game_id)

    # Oyuncu mu? (M2M listesinde var mı?)
    is_player = game.players.filter(id=request.user.id).exists()
    is_spectator = not is_player

    # Eğer izleyiciyse, ama oda bekliyorsa ve dolu değilse,
    # otomatik olarak 'join' (katıl) view'ine yönlendir.
    if is_spectator and game.status == 'waiting' and not game.is_full:
        return redirect('join_game', game_id=game.game_id)

    return render(request, 'game_room.html', {
        'game': game,
        'is_spectator': is_spectator,
        'game_id_json': str(game_id),
        'username_json': request.user.username,
        'initial_board_state_json': json.dumps(game.board_state or {}),

        # --- YENİ EKLENDİ ---
        # Tahta boyutunu template'e JSON olarak gönder
        'board_size_json': game.board_size
    })

# 4. ODAYA KATILMA (Tamamen Değişti)
@login_required
@transaction.atomic
def join_game(request, game_id):
    game = get_object_or_404(GameSession.objects.select_for_update(), game_id=game_id)
    game_slug = game.game_type.slug

    # Kontroller
    if game.players.filter(id=request.user.id).exists():
        messages.info(request, "Zaten bu odadasınız.")
        return redirect('game_room', game_id=game.game_id)
    if game.is_full:
        messages.error(request, "Oda dolu.")
        return redirect('game_specific_lobby', game_slug=game_slug)
    if game.status != 'waiting':
        messages.error(request, "Oyun çoktan başladı.")
        return redirect('game_specific_lobby', game_slug=game_slug)

    # Oyuncuyu 'players' M2M listesine ekle
    game.players.add(request.user)

    # Oda şimdi doldu mu? Dolduysa oyunu başlat.
    if game.is_full:
        game.status = 'in_progress'

        # Başlayacak oyuncuyu seç (Tüm oyuncular arasından)
        player_list = list(game.players.all())
        starter = random.choice(player_list)
        game.current_turn = starter
        game.save()

        # --- TÜM OYUNCULARA WEBSOCKET İLE HABER VER ---
        channel_layer = get_channel_layer()
        game_group_name = f"game_{game_id}"

        player_usernames = [p.username for p in player_list]

        async_to_sync(channel_layer.group_send)(
            game_group_name,
            {
                'type': 'game_message',
                'state': game.board_state,
                'turn': game.current_turn.username,
                'players': player_usernames,  # 'p1'/'p2' yerine tüm liste
                'status': game.status,
                'message': f"Oda doldu! {request.user.username} katıldı. Çark çevrildi ve {starter.username} başlıyor!",
                'special_event': 'game_start_roll'
            }
        )
    else:
        # Oda dolmadı, sadece yeni oyuncuyu kaydet
        game.save()
        # --- DİĞER OYUNCULARA HABER VER (Opsiyonel) ---
        # (WebSocket'e "Ahmet katıldı. (3/4)" mesajı gönder...)
        pass

    return redirect('game_room', game_id=game.game_id)





# 6. ODA SİLME (Kontroller değişti)
@login_required
def delete_game(request, game_id):
    game = get_object_or_404(GameSession, game_id=game_id)
    game_slug = game.game_type.slug  # Lobiye dönmek için

    # Sadece 'host' (kurucu) silebilir
    if game.host != request.user:
        messages.error(request, "Bu masayı siz oluşturmadınız.")
        return redirect('game_specific_lobby', game_slug=game_slug)
    if game.status != 'waiting':
        messages.error(request, "Oyun başladıktan sonra masa silinemez.")
        return redirect('game_specific_lobby', game_slug=game_slug)
    # Odada 1'den fazla kişi (yani kendinden başkası) varsa silemez
    if game.player_count > 1:
        messages.error(request, "Masada başkaları varken silemezsiniz.")
        return redirect('game_specific_lobby', game_slug=game_slug)

    game.delete()
    messages.success(request, "Masa başarıyla kapatıldı.")
    return redirect('game_specific_lobby', game_slug=game_slug)
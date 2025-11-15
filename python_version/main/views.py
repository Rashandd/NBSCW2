import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render

from .models import VoiceChannel, GameSession, MiniGame


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
    Filtreleme ve arama desteği ile.
    """
    # Sadece aktif oyunları göster
    minigames = MiniGame.objects.filter(is_active=True)
    
    # Arama filtresi
    search_query = request.GET.get('search', '')
    if search_query:
        minigames = minigames.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Oyuncu sayısı filtresi
    min_players_filter = request.GET.get('min_players')
    if min_players_filter:
        try:
            min_players_filter = int(min_players_filter)
            minigames = minigames.filter(min_players__lte=min_players_filter, max_players__gte=min_players_filter)
        except ValueError:
            pass
    
    max_players_filter = request.GET.get('max_players')
    if max_players_filter:
        try:
            max_players_filter = int(max_players_filter)
            minigames = minigames.filter(max_players__lte=max_players_filter)
        except ValueError:
            pass
    
    # Sıralama
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'players':
        minigames = minigames.order_by('min_players', 'max_players')
    elif sort_by == 'name':
        minigames = minigames.order_by('name')
    else:
        minigames = minigames.order_by('name')

    context = {
        'minigames_list': minigames,
        'search_query': search_query,
        'min_players_filter': min_players_filter,
        'max_players_filter': max_players_filter,
        'sort_by': sort_by,
    }
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

    if GameSession.objects.filter(game_type=game_type, host=request.user, status='waiting').exists():
        messages.warning(request, f"{game_type.name} için zaten bekleyen bir masanız var.")
        return redirect('game_specific_lobby', game_slug=game_slug)

    # --- TAHTA BOYUTU MANTIĞI BURADAN KALDIRILDI ---
    # Artık 'board_size' varsayılan (default=5) değeriyle oluşturulacak
    # ve oyun başladığında güncellenecek.

    game = GameSession.objects.create(
        game_type=game_type,
        host=request.user,
        current_turn=None,
        board_state={}
    )
    game.players.add(request.user)

    return redirect('game_room', game_id=game.game_id)


# 5. OYUN ODASI (DEĞİŞTİ)
@login_required
def game_room(request, game_id):
    game = get_object_or_404(GameSession.objects.select_related('game_type', 'host', 'current_turn', 'winner'),
                             game_id=game_id)
    is_player = game.players.filter(id=request.user.id).exists()
    is_spectator = not is_player

    if is_spectator and game.status == 'waiting' and not game.is_full:
        return redirect('join_game', game_id=game.game_id)

    return render(request, 'game_room.html', {
        'game': game,
        'is_spectator': is_spectator,
        'game_id_json': str(game_id),
        'username_json': request.user.username,
        'initial_board_state_json': json.dumps(game.board_state or {}),

        # --- YENİ EKLENDİ ---
        # Mevcut tahta boyutunu template'e gönder
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
    game.save()  # Oyuncuyu kaydet

    # --- OTOMATİK BAŞLATMA MANTIĞI KALDIRILDI ---

    # --- YENİ: Herkese haber ver ---
    # Odaya yeni biri katıldığında, odadaki herkese
    # güncel oyuncu listesini gönder (sayfa yenileme sorununu çözer)
    channel_layer = get_channel_layer()
    game_group_name = f"game_{game_id}"

    player_usernames = [p.username for p in game.players.all()]

    async_to_sync(channel_layer.group_send)(
        game_group_name,
        {
            'type': 'game_state',
            'state': game.board_state,
            'turn': None,
            'players': player_usernames,  # Güncellenmiş oyuncu listesi
            'status': game.status,
            'board_size': game.board_size,
            'message': f"{request.user.username} masaya katıldı.",
            'special_event': None
        }
    )

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
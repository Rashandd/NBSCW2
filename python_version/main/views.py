import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Case, When, FloatField, F
from django.db import models
from django.shortcuts import redirect, get_object_or_404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, VoiceChannel, GameSession, MiniGame


@login_required
def index(request):
    channels = VoiceChannel.objects.all().order_by('name')

    context = {
        'channels': channels,
        'title': _('Voice Chat Rooms'),
    }
    return render(request, 'index.html', context)


@login_required
def voice_channel_view(request, slug):
    """Tek bir sesli sohbet odası ve chat arayüzü."""

    channel = get_object_or_404(VoiceChannel, slug=slug)

    context = {
        'channel': channel,
        'title': _('#{channel_name} Room').format(channel_name=channel.name),
        # Kullanıcının oda slug'ını JavaScript'e aktarmak için
        'channel_slug': slug,
    }
    return render(request, 'oda.html', context)

@login_required
def settings_view(request):
    """Kullanıcının mikrofon/hoparlör seçimi yapacağı ayarlar sayfası."""
    return render(request, 'settings.html', {'title': _('Settings')})

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
        messages.warning(request, _("You already have a waiting table for {game_name}.").format(game_name=game_type.name))
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

    eliminated_players = game.eliminated_players if game.eliminated_players else []
    return render(request, 'game_room.html', {
        'game': game,
        'is_spectator': is_spectator,
        'game_id_json': str(game_id),
        'username_json': request.user.username,
        'initial_board_state_json': json.dumps(game.board_state or {}),
        'board_size_json': game.board_size,
        'eliminated_players_json': json.dumps(eliminated_players),
        'winner_json': game.winner.username if game.winner else None,
    })

# 4. ODAYA KATILMA (Tamamen Değişti)
@login_required
@transaction.atomic
def join_game(request, game_id):
    game = get_object_or_404(GameSession.objects.select_for_update(), game_id=game_id)
    game_slug = game.game_type.slug

    # Kontroller
    if game.players.filter(id=request.user.id).exists():
        messages.info(request, _("You are already in this room."))
        return redirect('game_room', game_id=game.game_id)
    if game.is_full:
        messages.error(request, _("Room is full."))
        return redirect('game_specific_lobby', game_slug=game_slug)
    if game.status != 'waiting':
        messages.error(request, _("Game has already started."))
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
            'message': _("{username} joined the table.").format(username=request.user.username),
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
        messages.error(request, _("You did not create this table."))
        return redirect('game_specific_lobby', game_slug=game_slug)
    if game.status != 'waiting':
        messages.error(request, _("Table cannot be deleted after the game has started."))
        return redirect('game_specific_lobby', game_slug=game_slug)
    # Odada 1'den fazla kişi (yani kendinden başkası) varsa silemez
    if game.player_count > 1:
        messages.error(request, _("You cannot delete the table while others are present."))
        return redirect('game_specific_lobby', game_slug=game_slug)

    game.delete()
    messages.success(request, _("Table closed successfully."))
    return redirect('game_specific_lobby', game_slug=game_slug)


@login_required
def leaderboard(request):
    """
    Liderlik tablosu - En iyi oyuncuları gösterir.
    """
    # Sıralama seçenekleri
    sort_by = request.GET.get('sort', 'rank_point')
    
    # Geçerli sıralama alanları
    valid_sorts = ['rank_point', 'total_wins', 'win_rate', 'total_games']
    if sort_by not in valid_sorts:
        sort_by = 'rank_point'
    
    # Sıralama yönü
    order = request.GET.get('order', 'desc')
    if order == 'asc':
        order_prefix = ''
    else:
        order_prefix = '-'
    
    # Kullanıcıları sırala
    if sort_by == 'win_rate':
        # Win rate için özel sorgu (property olduğu için)
        users = CustomUser.objects.filter(total_games__gt=0).annotate(
            calculated_win_rate=Case(
                When(total_games=0, then=0),
                default=F('total_wins') * 100.0 / F('total_games'),
                output_field=FloatField()
            )
        ).order_by(f'{order_prefix}calculated_win_rate', '-rank_point')
    else:
        users = CustomUser.objects.all().order_by(f'{order_prefix}{sort_by}', '-rank_point')
    
    # İlk 100 oyuncuyu al
    top_players = users[:100]
    
    # Kullanıcının sıralamasını bul
    user_rank = None
    if request.user.is_authenticated:
        try:
            user_rank = list(users.values_list('id', flat=True)).index(request.user.id) + 1
        except ValueError:
            pass
    
    context = {
        'top_players': top_players,
        'user_rank': user_rank,
        'current_user': request.user,
        'sort_by': sort_by,
        'order': order,
        'game_type': None,  # Global leaderboard
    }
    return render(request, 'leaderboard.html', context)


@login_required
def game_leaderboard(request, game_slug):
    """
    Belirli bir mini oyun için liderlik tablosu.
    per_game_stats JSONField üzerinden hesaplanır.
    """
    game_type = get_object_or_404(MiniGame, slug=game_slug)

    sort_by = request.GET.get('sort', 'rank_point')
    valid_sorts = ['rank_point', 'total_wins', 'win_rate', 'total_games']
    if sort_by not in valid_sorts:
        sort_by = 'rank_point'

    order = request.GET.get('order', 'desc')
    reverse = (order == 'desc')

    # JSONField içinden bu oyun için istatistiği olan kullanıcıları çek
    users_qs = CustomUser.objects.filter(per_game_stats__has_key=game_type.slug)
    players = []

    for user in users_qs:
        stats = user.per_game_stats.get(game_type.slug, {})
        g_games = stats.get("games", 0)
        g_wins = stats.get("wins", 0)
        g_losses = stats.get("losses", 0)
        g_rank = stats.get("rank_point", 0)
        g_win_rate = round((g_wins * 100.0 / g_games), 2) if g_games > 0 else 0.0

        # Runtime attribute'lar (template için)
        user.game_rank_point = g_rank
        user.game_total_wins = g_wins
        user.game_total_losses = g_losses
        user.game_total_games = g_games
        user.game_win_rate = g_win_rate
        players.append(user)

    # Python tarafında sıralama
    key_map = {
        'rank_point': lambda u: u.game_rank_point,
        'total_wins': lambda u: u.game_total_wins,
        'total_games': lambda u: u.game_total_games,
        'win_rate':   lambda u: u.game_win_rate,
    }
    players_sorted = sorted(players, key=key_map[sort_by], reverse=reverse)

    top_players = players_sorted[:100]

    user_rank = None
    if request.user.is_authenticated:
        try:
            user_ids_sorted = [u.id for u in players_sorted]
            user_rank = user_ids_sorted.index(request.user.id) + 1
        except ValueError:
            user_rank = None

    context = {
        'top_players': top_players,
        'user_rank': user_rank,
        'current_user': request.user,
        'sort_by': sort_by,
        'order': order,
        'game_type': game_type,  # Per-game leaderboard
    }
    return render(request, 'leaderboard.html', context)
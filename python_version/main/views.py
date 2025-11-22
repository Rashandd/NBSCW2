import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Case, When, FloatField, F, Value, IntegerField
from django.db import models
from django.shortcuts import redirect, get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.urls import reverse

from .models import CustomUser, Server, ServerRole, ServerMember, TextChannel, VoiceChannel, GameSession, MiniGame, ChatMessage, PrivateConversation, PrivateMessage
from django.utils.text import slugify
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings as django_settings


def index(request):
    """Landing page - shows servers if logged in"""
    if request.user.is_authenticated:
        # Get servers user is member of or owns
        my_servers = Server.objects.filter(
            Q(owner=request.user) | 
            Q(members__user=request.user)
        ).distinct().prefetch_related('members', 'text_channels', 'voice_channels').order_by('name')
        
        # Get all public servers that user is NOT a member of
        public_servers = Server.objects.filter(
            is_private=False
        ).exclude(
            Q(owner=request.user) | 
            Q(members__user=request.user)
        ).distinct().prefetch_related('members', 'text_channels', 'voice_channels').order_by('-created_at')[:12]
            
        context = {
            'my_servers': my_servers,
            'public_servers': public_servers,
            'title': _('Your Servers'),
            'user': request.user,
        }
        return render(request, 'index.html', context)
    
    # Not logged in state
    return render(request, 'index.html', {'title': _('Welcome to Rashigo')})


@login_required
def create_server(request):
    """Create a new server with default roles"""
    # Check server limit (e.g., max 5 servers per user)
    MAX_SERVERS_PER_USER = 5
    user_server_count = Server.objects.filter(owner=request.user).count()
    
    if user_server_count >= MAX_SERVERS_PER_USER:
        messages.error(request, _("You have reached the maximum limit of {limit} servers.").format(limit=MAX_SERVERS_PER_USER))
        return redirect('index')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_private = request.POST.get('is_private') == 'on'
        icon = request.POST.get('icon', '').strip() or None
        
        if not name:
            messages.error(request, _("Server name is required."))
            return render(request, 'create_server.html', {
                'title': _('Create Server'),
                'name': name,
                'description': description,
                'is_private': is_private,
                'icon': icon,
            })
        
        # Check if server name already exists
        if Server.objects.filter(name=name).exists():
            messages.error(request, _("A server with this name already exists. Please choose a different name."))
            return render(request, 'create_server.html', {
                'title': _('Create Server'),
                'name': name,
                'description': description,
                'is_private': is_private,
                'icon': icon,
            })
        
        try:
            # Create server
            server = Server.objects.create(
                name=name,
                description=description,
                owner=request.user,
                is_private=is_private,
                icon=icon
            )
            
            # Create default roles: Admin and Normal User
            admin_role = ServerRole.objects.create(
                server=server,
                name='Admin',
                color='#ff4444',
                position=100,  # Highest position
                permissions={
                    'manage_channels': True,
                    'manage_roles': True,
                    'kick_members': True,
                    'ban_members': True,
                    'manage_server': True,
                    'delete_messages': True,
                }
            )
            
            normal_user_role = ServerRole.objects.create(
                server=server,
                name='Normal User',
                color='#99aab5',
                position=0,  # Lowest position
                permissions={
                    'send_messages': True,
                    'read_messages': True,
                    'join_voice': True,
                }
            )
            
            # Auto-join creator to their own server with Admin role
            server_member = ServerMember.objects.create(
                server=server,
                user=request.user,
                is_online=True
            )
            server_member.roles.add(admin_role)
            
            messages.success(request, _("Server '{server_name}' created successfully!").format(server_name=server.name))
            return redirect('server_view', slug=server.slug)
            
        except Exception as e:
            messages.error(request, _("Error creating server: {error}").format(error=str(e)))
            return render(request, 'create_server.html', {
                'title': _('Create Server'),
                'name': name,
                'description': description,
                'is_private': is_private,
                'icon': icon,
            })
    
    # GET request - show form
    return render(request, 'create_server.html', {
        'title': _('Create Server'),
        'max_servers': MAX_SERVERS_PER_USER,
        'current_server_count': user_server_count,
    })


@login_required
def join_server(request):
    """Join a server using invite code (slug)"""
    if request.method == 'POST':
        invite_code = request.POST.get('invite_code', '').strip()
        
        if not invite_code:
            messages.error(request, _("Please enter an invite code."))
            return redirect('index')
        
        try:
            server = Server.objects.get(slug=invite_code)
            
            # Check if already a member
            is_member = server.owner == request.user or server.members.filter(user=request.user).exists()
            
            # If user is owner but not a ServerMember, create the membership
            if server.owner == request.user and not server.members.filter(user=request.user).exists():
                ServerMember.objects.get_or_create(
                    server=server,
                    user=request.user,
                    defaults={'is_online': True}
                )
                messages.success(request, _("Successfully joined {server_name}!").format(server_name=server.name))
                return redirect('server_view', slug=server.slug)
            
            # If already a member (but not owner), just redirect
            if is_member:
                messages.info(request, _("You are already a member of this server."))
                return redirect('server_view', slug=server.slug)
            
            # Check if private and user is not owner
            if server.is_private and server.owner != request.user:
                # For now, allow joining private servers with the code
                # In production, you might want an actual invite system
                pass
            
            # Create ServerMember
            ServerMember.objects.get_or_create(
                server=server,
                user=request.user,
                defaults={'is_online': True}
            )
            
            messages.success(request, _("Successfully joined {server_name}!").format(server_name=server.name))
            return redirect('server_view', slug=server.slug)
            
        except Server.DoesNotExist:
            messages.error(request, _("Invalid invite code. Please check and try again."))
            return redirect('index')
    
    return redirect('index')


@login_required
def server_view(request, slug):
    """View a server with its channels"""
    server = get_object_or_404(
        Server.objects.prefetch_related('text_channels', 'voice_channels', 'members__user', 'roles'),
        slug=slug
    )
    
    # Check if user is member or owner
    is_member = server.owner == request.user or server.members.filter(user=request.user).exists()
    
    # If user is owner but not a ServerMember, automatically create membership
    if server.owner == request.user and not server.members.filter(user=request.user).exists():
        ServerMember.objects.get_or_create(
            server=server,
            user=request.user,
            defaults={'is_online': True}
        )
        is_member = True
    
    if not is_member and server.is_private:
        messages.error(request, _("You don't have access to this server."))
        return redirect('index')
    
    # Get user's roles in this server
    member = server.members.filter(user=request.user).first()
    user_roles = member.roles.all() if member else []
    
    # Get COTURN settings from backend (one server handles all voice channels)
    coturn_config = getattr(django_settings, 'COTURN_CONFIG', {
        'stun_url': 'stun:31.58.244.167:3478',
        'turn_url': 'turn:31.58.244.167:3478',
        'turn_username': 'adem',
        'turn_credential': 'fb1907',
        'stun_url_2': 'stun:stun.l.google.com:19302',
    })
    
    # Serialize COTURN config as JSON for JavaScript
    coturn_config_json = json.dumps(coturn_config, cls=DjangoJSONEncoder)
    
    # Include all members (owner is also a member and should be shown)
    # Order: owner first, then by joined_at
    members = server.members.select_related('user').annotate(
        is_owner_field=Case(
            When(user=server.owner, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('-is_owner_field', 'joined_at')
    
    # Get current user's member object for permission checking
    current_member = server.members.filter(user=request.user).first()
    if server.owner == request.user:
        # Owner has all permissions, create a dummy member object
        from .models import ServerMember
        current_member = type('obj', (object,), {
            'has_permission': lambda perm: True,
            'can_access_channel': lambda ch: True,
            'roles': server.roles.none()
        })()
    
    # Filter channels based on permissions
    accessible_text_channels = []
    accessible_voice_channels = []
    
    for channel in server.text_channels.all():
        if current_member and current_member.can_access_channel(channel):
            accessible_text_channels.append(channel)
    
    for channel in server.voice_channels.all():
        if current_member and current_member.can_access_channel(channel):
            accessible_voice_channels.append(channel)
    
    context = {
        'server': server,
        'user': request.user,
        'is_owner': server.owner == request.user,
        'is_member': is_member,
        'user_roles': user_roles,
        'current_member': current_member,
        'text_channels': accessible_text_channels,  # Filtered by permissions
        'voice_channels': accessible_voice_channels,  # Filtered by permissions
        'members': members,  # Owner included and shown first
        'coturn_config': coturn_config,  # For template display
        'coturn_config_json': coturn_config_json,  # For JavaScript
    }
    return render(request, 'server_view.html', context)


@login_required
def channel_view(request, server_slug, channel_slug):
    """View a text channel in a server"""
    server = get_object_or_404(Server, slug=server_slug)
    channel = get_object_or_404(TextChannel, server=server, slug=channel_slug)
    
    # Check if user is member
    is_member = server.owner == request.user or server.members.filter(user=request.user).exists()
    if not is_member and server.is_private:
        messages.error(request, _("You don't have access to this server."))
        return redirect('index')
    
    # Check channel permissions
    member = server.members.filter(user=request.user).first()
    if server.owner != request.user:
        if not member or not member.can_access_channel(channel):
            messages.error(request, _("You don't have permission to access this channel."))
            return redirect('server_view', slug=server.slug)
    
    # Get recent messages
    recent_messages = ChatMessage.objects.filter(channel=channel).select_related('user').order_by('-created_at')[:50]
    recent_messages = list(reversed(recent_messages))
    
    context = {
        'server': server,
        'channel': channel,
        'user': request.user,
        'recent_messages': recent_messages,
    }
    return render(request, 'channel_view.html', context)


@login_required
def voice_channel_view(request, slug):
    """Tek bir sesli sohbet odası ve chat arayüzü."""

    channel = get_object_or_404(VoiceChannel, slug=slug)
    
    # Get recent chat messages (last 50)
    recent_messages = ChatMessage.objects.filter(channel=channel).select_related('user').order_by('-created_at')[:50]
    recent_messages = list(reversed(recent_messages))  # Reverse to show oldest first
    
    # Get online and all members (from the server if it exists)
    if channel.server:
        online_members = ServerMember.objects.filter(server=channel.server, is_online=True).select_related('user')
        all_members = ServerMember.objects.filter(server=channel.server).select_related('user')
    else:
        # Legacy channels without server - no members to show
        online_members = []
        all_members = []

    context = {
        'channel': channel,
        'title': _('#{channel_name} Room').format(channel_name=channel.name),
        'channel_slug': slug,
        'user': request.user,
        'recent_messages': recent_messages,
        'online_members': online_members,
        'all_members': all_members,
    }
    return render(request, 'oda.html', context)


@login_required
def chat_messages_api(request, slug):
    """API endpoint to fetch chat messages for a channel (TextChannel or VoiceChannel)"""
    # Try TextChannel first, then VoiceChannel
    channel = None
    try:
        channel = TextChannel.objects.get(slug=slug)
    except TextChannel.DoesNotExist:
        try:
            channel = VoiceChannel.objects.get(slug=slug)
        except VoiceChannel.DoesNotExist:
            return JsonResponse({'error': 'Channel not found'}, status=404)
    
    limit = int(request.GET.get('limit', 50))
    
    messages = ChatMessage.objects.filter(channel=channel).select_related('user').order_by('-created_at')[:limit]
    
    messages_data = [
        {
            'id': msg.id,
            'author': msg.user.username,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat(),
            'created_at': msg.created_at.strftime('%I:%M %p'),
        }
        for msg in reversed(messages)
    ]
    
    return JsonResponse({'messages': messages_data})

@login_required
def settings_view(request):
    """User settings page with account management and preferences."""
    user = request.user
    owned_servers = Server.objects.filter(owner=user).count()
    member_servers = Server.objects.filter(members__user=user).exclude(owner=user).distinct().count()
    
    # Get COTURN settings from backend (read-only, configured by admin)
    coturn_config = getattr(django_settings, 'COTURN_CONFIG', {
        'stun_url': 'stun:31.58.244.167:3478',
        'turn_url': 'turn:31.58.244.167:3478',
        'turn_username': 'adem',
        'turn_credential': 'fb1907',
        'stun_url_2': 'stun:stun.l.google.com:19302',
    })
    
    context = {
        'title': _('Settings'),
        'user': user,
        'owned_servers': owned_servers,
        'member_servers': member_servers,
        'coturn_config': coturn_config,  # Backend COTURN settings (read-only)
    }
    return render(request, 'settings.html', context)


@login_required
def create_text_channel(request, server_slug):
    """Create a text channel in a server (owner only, max 100)"""
    server = get_object_or_404(Server, slug=server_slug)
    
    # Check if user is owner
    if server.owner != request.user:
        messages.error(request, _("Only the server owner can create channels."))
        return redirect('server_view', slug=server_slug)
    
    # Check channel limit (100 total: text + voice)
    total_channels = server.text_channels.count() + server.voice_channels.count()
    if total_channels >= 100:
        messages.error(request, _("Maximum channel limit reached (100 channels)."))
        return redirect('server_view', slug=server_slug)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        position = int(request.POST.get('position', 0))
        is_private = request.POST.get('is_private') == 'on'
        
        if not name:
            messages.error(request, _("Channel name is required."))
            return redirect('server_view', slug=server_slug)
        
        try:
            TextChannel.objects.create(
                server=server,
                name=name,
                description=description,
                position=position,
                is_private=is_private
            )
            messages.success(request, _("Text channel '{name}' created successfully!").format(name=name))
        except Exception as e:
            messages.error(request, _("Error creating channel: {error}").format(error=str(e)))
    
    return redirect('server_view', slug=server_slug)


@login_required
def create_voice_channel(request, server_slug):
    """Create a voice channel in a server (owner only, max 100)"""
    server = get_object_or_404(Server, slug=server_slug)
    
    # Check if user is owner
    if server.owner != request.user:
        messages.error(request, _("Only the server owner can create channels."))
        return redirect('server_view', slug=server_slug)
    
    # Check channel limit (100 total: text + voice)
    total_channels = server.text_channels.count() + server.voice_channels.count()
    if total_channels >= 100:
        messages.error(request, _("Maximum channel limit reached (100 channels)."))
        return redirect('server_view', slug=server_slug)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        position = int(request.POST.get('position', 0))
        user_limit = int(request.POST.get('user_limit', 0))
        is_private = request.POST.get('is_private') == 'on'
        
        if not name:
            messages.error(request, _("Channel name is required."))
            return redirect('server_view', slug=server_slug)
        
        try:
            VoiceChannel.objects.create(
                server=server,
                name=name,
                description=description,
                position=position,
                user_limit=user_limit,
                is_private=is_private
            )
            messages.success(request, _("Voice channel '{name}' created successfully!").format(name=name))
        except Exception as e:
            messages.error(request, _("Error creating channel: {error}").format(error=str(e)))
    
    return redirect('server_view', slug=server_slug)

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
        status__in=['waiting', 'in_progress']
    ).filter(
        Q(players=request.user) | Q(invited_players__contains=[request.user.username])
    ).select_related('game_type', 'host').order_by('-created_at')

    # 2. Katılınabilecek Masalar (Dolu olmayan, beklemede olan, içinde olmadığım)
    max_p = game_type.max_players
    available_games = GameSession.objects.filter(
        game_type=game_type,
        status='waiting',
        is_private=False
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


@login_required
def rematch_request(request, game_id):
    if request.method != 'POST':
        return JsonResponse({'error': _('Invalid request method.')}, status=405)

    game = get_object_or_404(
        GameSession.objects.select_related('game_type', 'host').prefetch_related('players'),
        game_id=game_id
    )

    if game.status != 'finished':
        return JsonResponse({'error': _('Game has not finished yet.')}, status=400)

    if not game.players.filter(id=request.user.id).exists():
        return JsonResponse({'error': _('You are not part of this game.')}, status=403)

    existing_waiting = GameSession.objects.filter(
        game_type=game.game_type,
        host=request.user,
        status='waiting'
    ).order_by('-created_at').first()

    if existing_waiting:
        return JsonResponse({
            'new_game_id': str(existing_waiting.game_id),
            'redirect_url': reverse('game_room', args=[existing_waiting.game_id])
        })

    invited_players = [player.username for player in game.players.all() if player != request.user]

    new_game = GameSession.objects.create(
        game_type=game.game_type,
        host=request.user,
        status='waiting',
        board_state={},
        board_size=game.board_size,
        is_private=True,
        invited_players=invited_players,
        rematch_parent=game
    )
    new_game.players.add(request.user)

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"game_{game_id}",
        {
            'type': 'rematch_invite',
            'new_game_id': str(new_game.game_id),
            'host': request.user.username,
            'invited_players': invited_players,
            'game_room_url': reverse('game_room', args=[new_game.game_id]),
            'join_url': reverse('join_game', args=[new_game.game_id]),
            'message': _("Rematch requested by {username}.").format(username=request.user.username)
        }
    )

    return JsonResponse({
        'new_game_id': str(new_game.game_id),
        'redirect_url': reverse('game_room', args=[new_game.game_id])
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
    if game.is_private:
        allowed = request.user.username in (game.invited_players or []) or request.user == game.host
        if not allowed:
            messages.error(request, _("This table is private and you are not invited."))
            return redirect('game_specific_lobby', game_slug=game_slug)
    if game.is_full:
        messages.error(request, _("Room is full."))
        return redirect('game_specific_lobby', game_slug=game_slug)
    if game.status != 'waiting':
        messages.error(request, _("Game has already started."))
        return redirect('game_specific_lobby', game_slug=game_slug)

    # Oyuncuyu 'players' M2M listesine ekle
    game.players.add(request.user)
    if game.is_private and game.invited_players:
        updated_invites = list(game.invited_players)
        if request.user.username in updated_invites:
            updated_invites.remove(request.user.username)
        game.invited_players = updated_invites
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


# User Profile Views
@login_required
def user_profile_api(request, username):
    """API endpoint to get user profile"""
    try:
        user = CustomUser.objects.get(username=username)
        return JsonResponse({
            'username': user.username,
            'bio': getattr(user, 'bio', ''),
            'rank_point': user.rank_point or 0,
            'date_joined': user.date_joined.isoformat(),
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


# Private Messaging Views
@login_required
def private_messages_api(request, username):
    """Get private messages with a user"""
    try:
        other_user = CustomUser.objects.get(username=username)
        
        # Get or create conversation
        conversation = PrivateConversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).distinct().first()
        
        if not conversation:
            conversation = PrivateConversation.objects.create()
            conversation.participants.add(request.user, other_user)
        
        messages = PrivateMessage.objects.filter(
            conversation=conversation
        ).select_related('sender').order_by('created_at')
        
        # Mark messages as read
        PrivateMessage.objects.filter(
            conversation=conversation,
            sender=other_user,
            is_read=False
        ).update(is_read=True)
        
        messages_data = [{
            'sender': msg.sender.username,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat(),
            'is_read': msg.is_read,
        } for msg in messages]
        
        return JsonResponse({'messages': messages_data})
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


@login_required
def send_private_message_api(request, username):
    """Send a private message to a user"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        other_user = CustomUser.objects.get(username=username)
        
        if other_user == request.user:
            return JsonResponse({'error': 'Cannot message yourself'}, status=400)
        
        content = json.loads(request.body).get('content', '').strip()
        if not content:
            return JsonResponse({'error': 'Message content required'}, status=400)
        
        # Get or create conversation
        conversation = PrivateConversation.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).distinct().first()
        
        if not conversation:
            conversation = PrivateConversation.objects.create()
            conversation.participants.add(request.user, other_user)
        
        # Create message
        message = PrivateMessage.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'message': {
                'sender': message.sender.username,
                'content': message.content,
                'timestamp': message.created_at.isoformat(),
            }
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
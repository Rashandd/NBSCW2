# kullanicilar/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

import uuid
from django.db.models import JSONField
from django.template.defaultfilters import truncatechars
from django.utils.text import slugify


class CustomUser(AbstractUser):
    # AbstractUser, username, first_name, last_name, email, is_staff, is_active, date_joined gibi alanları zaten içerir.

    rank_point = models.PositiveIntegerField(null=True, blank=True, default=0)
    total_wins = models.PositiveIntegerField(default=0, verbose_name="Toplam Kazanma")
    total_losses = models.PositiveIntegerField(default=0, verbose_name="Toplam Kayıp")
    total_games = models.PositiveIntegerField(default=0, verbose_name="Toplam Oyun")
    # Oyun bazlı istatistikler:
    # {
    #   "dice-wars": {"rank_point": 120, "wins": 4, "losses": 2, "games": 6},
    #   "another-game": {...}
    # }
    per_game_stats = JSONField(default=dict, verbose_name="Oyun Bazlı İstatistikler")
    
    @property
    def win_rate(self):
        """Kazanma oranını hesaplar (0-100)"""
        if self.total_games == 0:
            return 0.0
        return round((self.total_wins / self.total_games) * 100, 2)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',  # Burayı değiştirdik
        blank=True,
        help_text=('The groups this user belongs to. A user will get all permissions '
                   'granted to each of their groups.'),
        verbose_name=('groups'),
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',  # Burayı değiştirdik
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name=('user permissions'),
    )
    def __str__(self):
        # Admin panelinde ve diğer yerlerde nasıl görüneceğini belirler
        return self.username


class Server(models.Model):
    """Servers contain channels, roles, and members"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_servers')
    icon = models.CharField(max_length=100, blank=True, null=True, help_text="Icon name or emoji")
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ServerRole(models.Model):
    """Roles within a server (e.g., Admin, Moderator, Member)"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#99aab5', help_text="Hex color code")
    permissions = models.JSONField(default=dict, help_text="Dictionary of permission flags")
    position = models.IntegerField(default=0, help_text="Higher position = higher priority")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-position', 'name']
        unique_together = ('server', 'name')

    def __str__(self):
        return f"{self.server.name} - {self.name}"


class ServerMember(models.Model):
    """Users belonging to servers with roles"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='server_memberships')
    roles = models.ManyToManyField(ServerRole, blank=True, related_name='members')
    nickname = models.CharField(max_length=100, blank=True, null=True)
    joined_at = models.DateTimeField(auto_now=True)
    is_online = models.BooleanField(default=False)

    class Meta:
        unique_together = ('server', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.server.name}"

    def get_display_name(self):
        return self.nickname or self.user.username


class TextChannel(models.Model):
    """Text channels for chat messages"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='text_channels', null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    position = models.IntegerField(default=0)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'name']
        # Remove unique_together since server can be null - slug uniqueness will be handled at application level

    def __str__(self):
        server_name = self.server.name if self.server else "No Server"
        return f"{server_name} - #{self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class VoiceChannel(models.Model):
    """Voice channels for voice communication"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='voice_channels', null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    position = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=0, help_text="0 = unlimited")
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'name']
        # Remove unique_together since server can be null - slug uniqueness will be handled at application level

    def __str__(self):
        server_name = self.server.name if self.server else "No Server"
        return f"{server_name} - 🔊 {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """Chat messages stored in text channels"""
    channel = models.ForeignKey(TextChannel, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['channel', 'created_at']),
        ]

    def __str__(self):
        if self.channel:
            return f"{self.user.username} in #{self.channel.name}: {self.content[:50]}"
        return f"{self.user.username}: {self.content[:50]}"




# 5x5'lik boş bir tahta oluşturan varsayılan fonksiyon
def default_board():
    return [[None for _ in range(5)] for _ in range(5)]
    # Her hücre: { 'owner': 'username', 'count': 2 } veya None olabilir


class MiniGame(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Oyun Adı")
    slug = models.SlugField(max_length=100, unique=True, editable=False)
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    min_players = models.PositiveSmallIntegerField(default=2, verbose_name="Min. Oyuncu")
    max_players = models.PositiveSmallIntegerField(default=2, verbose_name="Max. Oyuncu")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Mini Oyun"
        verbose_name_plural = "Mini Oyunlar"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class GameSession(models.Model):
    game_type = models.ForeignKey(
        MiniGame,
        on_delete=models.PROTECT,
        related_name='sessions',
        default=None,
        null=True
    )
    STATUS_CHOICES = [
        ('waiting', 'Oyuncu Bekliyor'),
        ('in_progress', 'Devam Ediyor'),
        ('finished', 'Bitti'),
    ]
    game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='hosted_games',
        on_delete=models.CASCADE,
        default=None,
        null=True
    )
    players = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='game_sessions',
        blank=True
    )
    board_state = models.JSONField(default=dict)

    # --- YENİ EKLENEN ALAN ---
    # Oyuncu sayısına göre tahta boyutunu burada saklayacağız
    board_size = models.PositiveSmallIntegerField(default=5, verbose_name="Tahta Boyutu (N x N)")
    # --------------------------

    current_turn = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    winner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='games_won', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    move_count = models.PositiveIntegerField(default=0, verbose_name="Hamle Sayısı")
    eliminated_players = models.JSONField(default=list, verbose_name="Elenmiş Oyuncular")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Bitiş Zamanı")
    is_private = models.BooleanField(default=False, verbose_name="Özel Oda")
    invited_players = models.JSONField(default=list, blank=True, verbose_name="Davetli Oyuncular")
    rematch_parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rematch_children'
    )

    @property
    def player_count(self):
        return self.players.count()

    @property
    def is_full(self):
        return self.players.count() >= self.game_type.max_players

    @property
    def is_ready_to_start(self):
        return self.players.count() >= self.game_type.min_players

    def __str__(self):
        id_str = str(self.game_id)
        truncated_id = truncatechars(id_str, 8)
        return f"Masa {truncated_id}"
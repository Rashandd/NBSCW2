# kullanicilar/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField
from django.template.defaultfilters import truncatechars
from django.utils.text import slugify


class CustomUser(AbstractUser):
    # AbstractUser, username, first_name, last_name, email, is_staff, is_active, date_joined gibi alanları zaten içerir.

    rank_point = models.PositiveIntegerField(null=True, blank=True,default=0)
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


class VoiceChannel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)  # URL'lerde kullanmak için
    is_private = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class ChannelMember(models.Model):
    # Foreign Key'de CustomUser'a referans vermek için settings.AUTH_USER_MODEL kullanıyoruz
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    channel = models.ForeignKey(VoiceChannel, on_delete=models.CASCADE)
    is_online = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'channel')

    def __str__(self):
        return f"{self.user.username} - {self.channel.name}"




# 5x5'lik boş bir tahta oluşturan varsayılan fonksiyon
def default_board():
    return [[None for _ in range(5)] for _ in range(5)]
    # Her hücre: { 'owner': 'username', 'count': 2 } veya None olabilir


class MiniGame(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Oyun Adı")
    slug = models.SlugField(max_length=100, unique=True, editable=False)
    description = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    # --- YENİ ALANLAR ---
    # Her oyunun kaç kişiyle oynandığını belirtmeliyiz
    min_players = models.PositiveSmallIntegerField(default=2, verbose_name="Min. Oyuncu")
    max_players = models.PositiveSmallIntegerField(default=2, verbose_name="Max. Oyuncu")

    # (Dice Wars için 2, Ludo için 4 vb. admin panelden ayarlayabilirsiniz)
    # ----------------------

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

    # --- TEMEL DEĞİŞİKLİK ---
    # player1 yerine 'host' (Oda Kurucusu)
    host = models.ForeignKey(
        User,
        related_name='hosted_games',
        on_delete=models.CASCADE,
        default=None,
        null=True
    )
    # player2 yerine 'players' (Tüm oyuncular, M2M)
    players = models.ManyToManyField(
        User,
        related_name='game_sessions',
        blank=True
    )
    # --------------------------

    board_state = models.JSONField(default=dict)
    current_turn = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    winner = models.ForeignKey(User, related_name='games_won', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- YENİ YARDIMCI METOTLAR ---
    @property
    def player_count(self):
        """O anki oyuncu sayısını döndürür."""
        return self.players.count()

    @property
    def is_full(self):
        """Oda dolu mu?"""
        return self.players.count() >= self.game_type.max_players

    @property
    def is_ready_to_start(self):
        """Oyunun başlaması için yeterli oyuncu var mı?"""
        return self.players.count() >= self.game_type.min_players

    # ------------------------------

    def __str__(self):
        return f"{self.game_type.name} Masası ({self.game_id | truncatechars:8})"
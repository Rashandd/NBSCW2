# kullanicilar/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

import uuid
from django.db.models import JSONField
from django.template.defaultfilters import truncatechars
from django.utils.text import slugify


class CustomUser(AbstractUser):
    """
    Flexible and dynamic user model with extensible JSON fields.
    Supports custom attributes, preferences, and metadata without schema changes.
    """
    # Core game/profile fields
    rank_point = models.PositiveIntegerField(null=True, blank=True, default=0)
    total_games = models.PositiveIntegerField(default=0, help_text="Total games played")
    total_wins = models.PositiveIntegerField(default=0, help_text="Total games won")
    total_losses = models.PositiveIntegerField(default=0, help_text="Total games lost")
    avatar_url = models.URLField(blank=True, null=True, help_text="User avatar image URL")
    bio = models.TextField(blank=True, null=True, max_length=500, help_text="User biography")
    
    # Flexible JSON fields for extensibility
    user_settings = models.JSONField(
        default=dict, 
        blank=True, 
        null=True,
        help_text="User preferences and settings (theme, notifications, etc.)"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Additional user metadata (custom fields, stats, etc.)"
    )
    per_game_stats = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Statistics per game type"
    )
    
    # Activity tracking
    last_activity = models.DateTimeField(auto_now=True, null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Status fields
    is_online = models.BooleanField(default=False)
    status_message = models.CharField(max_length=200, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_online', 'last_activity']),
        ]

    def __str__(self):
        return self.username
    
    def get_display_name(self):
        """Get display name (nickname or username)"""
        return self.metadata.get('display_name') or self.username
    
    def get_avatar(self):
        """Get avatar URL or default"""
        return self.avatar_url or f"https://ui-avatars.com/api/?name={self.username}&background=random"
    
    def update_setting(self, key, value):
        """Update a user setting"""
        if not self.user_settings:
            self.user_settings = {}
        self.user_settings[key] = value
        self.save(update_fields=['user_settings'])
    
    def get_setting(self, key, default=None):
        """Get a user setting"""
        return self.user_settings.get(key, default) if self.user_settings else default
    
    def update_metadata(self, key, value):
        """Update user metadata"""
        if not self.metadata:
            self.metadata = {}
        self.metadata[key] = value
        self.save(update_fields=['metadata'])
    
    def get_metadata(self, key, default=None):
        """Get user metadata"""
        return self.metadata.get(key, default) if self.metadata else default
    
    @property
    def win_rate(self):
        """Calculate win rate percentage"""
        if self.total_games == 0:
            return 0.0
        return round((self.total_wins * 100.0) / self.total_games, 2)


class Server(models.Model):
    """
    Flexible and dynamic server model with extensible JSON fields.
    Supports custom settings, features, and metadata without schema changes.
    """
    # Core server fields
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True, max_length=1000)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_servers'
    )
    icon = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Icon name or emoji"
    )
    banner_url = models.URLField(
        blank=True, 
        null=True, 
        help_text="Server banner image URL"
    )
    
    # Privacy and visibility
    is_private = models.BooleanField(
        default=False,
        help_text="Private servers require invitation"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Verified servers (official/trusted)"
    )
    
    # Flexible JSON fields for extensibility
    settings = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Server settings (notifications, moderation, etc.)"
    )
    features = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Enabled features and capabilities"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Additional server metadata (custom fields, stats, etc.)"
    )
    
    # Limits and constraints
    max_members = models.PositiveIntegerField(
        default=1000,
        null=True,
        blank=True,
        help_text="Maximum number of members (null = unlimited)"
    )
    max_channels = models.PositiveIntegerField(
        default=100,
        null=True,
        blank=True,
        help_text="Maximum number of channels (null = unlimited)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['owner', 'created_at']),
            models.Index(fields=['is_private', 'is_verified']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_member_count(self):
        """Get current member count"""
        return self.members.count() + 1  # +1 for owner
    
    def can_add_member(self):
        """Check if server can accept more members"""
        if self.max_members is None:
            return True
        return self.get_member_count() < self.max_members
    
    def can_add_channel(self):
        """Check if server can add more channels"""
        if self.max_channels is None:
            return True
        total_channels = self.text_channels.count() + self.voice_channels.count()
        return total_channels < self.max_channels
    
    def update_setting(self, key, value):
        """Update a server setting"""
        if not self.settings:
            self.settings = {}
        self.settings[key] = value
        self.save(update_fields=['settings'])
    
    def get_setting(self, key, default=None):
        """Get a server setting"""
        return self.settings.get(key, default) if self.settings else default
    
    def enable_feature(self, feature_name):
        """Enable a server feature"""
        if not self.features:
            self.features = {}
        self.features[feature_name] = True
        self.save(update_fields=['features'])
    
    def disable_feature(self, feature_name):
        """Disable a server feature"""
        if not self.features:
            self.features = {}
        self.features[feature_name] = False
        self.save(update_fields=['features'])
    
    def has_feature(self, feature_name):
        """Check if a feature is enabled"""
        return self.features.get(feature_name, False) if self.features else False
    
    def update_metadata(self, key, value):
        """Update server metadata"""
        if not self.metadata:
            self.metadata = {}
        self.metadata[key] = value
        self.save(update_fields=['metadata'])
    
    def get_metadata(self, key, default=None):
        """Get server metadata"""
        return self.metadata.get(key, default) if self.metadata else default


class ServerRole(models.Model):
    """Roles within a server (e.g., Admin, Moderator, Member)"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#99aab5', help_text="Hex color code")
    permissions = models.JSONField(default=dict, help_text="Dictionary of permission flags")
    position = models.IntegerField(default=0, help_text="Higher position = higher priority")
    created_at = models.DateTimeField(auto_now_add=True)

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
    joined_at = models.DateTimeField(auto_now_add=True)
    is_online = models.BooleanField(default=False)

    class Meta:
        unique_together = ('server', 'user')
        ordering = ['joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.server.name}"

    def get_display_name(self):
        return self.nickname or self.user.username
    
    def has_permission(self, permission_name):
        """Check if member has a specific permission through their roles"""
        if self.server.owner == self.user:
            return True  # Owner has all permissions
        
        for role in self.roles.all():
            if role.permissions.get(permission_name, False):
                return True
        return False
    
    def can_access_channel(self, channel):
        """Check if member can access a channel based on allowed_roles"""
        if self.server.owner == self.user:
            return True  # Owner can access all channels
        
        # If channel has no allowed_roles, everyone can access
        if hasattr(channel, 'allowed_roles') and channel.allowed_roles.exists():
            # Check if user has any of the allowed roles
            user_roles = self.roles.all()
            return channel.allowed_roles.filter(id__in=user_roles.values_list('id', flat=True)).exists()
        
        return True  # Default: accessible to all


class TextChannel(models.Model):
    """Text channels for chat messages"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='text_channels', null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    position = models.IntegerField(default=0)
    is_private = models.BooleanField(default=False)
    allowed_roles = models.ManyToManyField(ServerRole, blank=True, related_name='text_channels', help_text="Roles that can access this channel. Empty = all roles")
    created_at = models.DateTimeField(auto_now_add=True)

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
    allowed_roles = models.ManyToManyField(ServerRole, blank=True, related_name='voice_channels', help_text="Roles that can access this channel. Empty = all roles")
    created_at = models.DateTimeField(auto_now_add=True)

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
    """Messages in text channels"""
    channel = models.ForeignKey(TextChannel, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['channel', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.channel.name}: {truncatechars(self.content, 50)}"


# Private Message System
class PrivateConversation(models.Model):
    """Private conversation between two users"""
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='private_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Private: {', '.join([p.username for p in self.participants.all()])}"


class PrivateMessage(models.Model):
    """Private messages between users"""
    conversation = models.ForeignKey(PrivateConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_private_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]

    def __str__(self):
        return f"{self.sender.username}: {truncatechars(self.content, 50)}"


class MiniGame(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    min_players = models.PositiveIntegerField(default=2)
    max_players = models.PositiveIntegerField(default=4)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

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
    created_at = models.DateTimeField(auto_now_add=True)
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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.game_type.name} - {self.game_id}"

    @property
    def player_count(self):
        """Get current number of players"""
        return self.players.count()
    
    @property
    def is_full(self):
        return self.players.count() >= self.game_type.max_players


# AI Agent Models
class AIAgent(models.Model):
    """AI Agent configuration"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    agent_type = models.CharField(
        max_length=50,
        choices=[
            ('assistant', 'Assistant'),
            ('workflow', 'Workflow Automation'),
            ('conversational', 'Conversational'),
        ],
        default='assistant'
    )
    system_prompt = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    max_memory_entries = models.PositiveIntegerField(default=1000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Workflow(models.Model):
    """Workflow definition for automation"""
    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True, null=True)
    steps = models.JSONField(default=list, help_text="List of workflow steps")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('agent', 'slug')

    def __str__(self):
        return f"{self.agent.name} - {self.name}"


class WorkflowExecution(models.Model):
    """Workflow execution tracking"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workflow_executions', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.workflow.name} - {self.status}"


class MemoryBank(models.Model):
    """AI memory storage with semantic search capabilities"""
    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='memories', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_memories', null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    memory_type = models.CharField(
        max_length=50,
        choices=[
            ('conversation', 'Conversation'),
            ('context', 'Context'),
            ('knowledge', 'Knowledge'),
            ('preference', 'Preference'),
        ],
        default='context'
    )
    context = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    priority = models.IntegerField(default=2, help_text="1=Critical, 2=High, 3=Medium, 4=Low")
    relevance_score = models.FloatField(default=0.0)
    access_count = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    source_type = models.CharField(max_length=50, null=True, blank=True, help_text="e.g., 'conversation', 'workflow', 'manual'")
    source_id = models.CharField(max_length=100, null=True, blank=True)
    embedding = models.JSONField(null=True, blank=True, help_text="Vector embedding for semantic search")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    related_memories = models.ManyToManyField('self', symmetrical=True, blank=True)

    class Meta:
        ordering = ['-relevance_score', '-updated_at']
        indexes = [
            models.Index(fields=['agent', 'memory_type']),
            models.Index(fields=['user', 'memory_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.memory_type})"

# main/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import (
    MiniGame, GameSession, VoiceChannel, Server, ServerRole, 
    ServerMember, TextChannel, ChatMessage, Workflow, WorkflowExecution,
    MemoryBank, AIAgent
)

User = get_user_model()


@admin.register(MiniGame)
class MiniGameAdmin(admin.ModelAdmin):
    """
    MiniGame modeli için gelişmiş admin ayarları.
    Oyunları dinamik olarak eklemek ve yönetmek için optimize edilmiş.
    """
    list_display = ['name', 'slug', 'min_players', 'max_players', 'is_active', 'active_sessions_count', 'created_at']
    list_filter = ['is_active', 'min_players', 'max_players', 'created_at']
    search_fields = ['name', 'description', 'slug']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Oyuncu Ayarları', {
            'fields': ('min_players', 'max_players')
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        from django.db.models import Q
        qs = super().get_queryset(request)
        return qs.annotate(
            active_sessions=Count('sessions', filter=Q(sessions__status__in=['waiting', 'in_progress']))
        )
    
    def active_sessions_count(self, obj):
        """Aktif oyun sayısını gösterir"""
        if hasattr(obj, 'active_sessions'):
            return obj.active_sessions
        return obj.sessions.filter(status__in=['waiting', 'in_progress']).count()
    
    active_sessions_count.short_description = 'Aktif Oyunlar'
    active_sessions_count.admin_order_field = 'active_sessions'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    CustomUser modeli için özel admin ayarları.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'rank_point', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Oyun Bilgileri', {
            'fields': ('rank_point',)
        }),
    )
@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    """
    GameSession modeli için admin ayarları.
    """
    list_display = (
        '__str__', 'game_type', 'host', 'status',
        'player_count_display', 'board_size', 'created_at'
    )
    list_filter = ('status', 'game_type', 'created_at')
    search_fields = ('game_id', 'host__username')

    readonly_fields = (
        'game_id', 'created_at', 'player_count_display', 'players_list'
    )

    fields = (
        'game_id', 'game_type', 'host', 'status', 'board_size',
        'current_turn', 'winner', 'players_list', 'board_state'
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'game_type', 'host'
        ).prefetch_related('players')

    def player_count_display(self, obj):
        return f"{obj.player_count} / {obj.game_type.max_players}"

    player_count_display.short_description = "Oyuncular"

    def players_list(self, obj):
        return ", ".join([p.username for p in obj.players.all()])

    players_list.short_description = "Katılan Oyuncular"

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    """Admin interface for Server model"""
    list_display = ('icon_display', 'name', 'owner', 'member_count', 'channel_count', 'is_private', 'created_at')
    list_filter = ('is_private', 'created_at')
    search_fields = ('name', 'slug', 'description', 'owner__username')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description', 'owner')
        }),
        ('Settings', {
            'fields': ('is_private',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def icon_display(self, obj):
        """Display server icon"""
        if obj.icon:
            return format_html('<span style="font-size: 20px;">{}</span>', obj.icon)
        return format_html('<i class="fas fa-server"></i>')
    icon_display.short_description = 'Icon'
    
    def member_count(self, obj):
        """Display member count"""
        return obj.members.count()
    member_count.short_description = 'Members'
    
    def channel_count(self, obj):
        """Display total channel count"""
        text = obj.text_channels.count()
        voice = obj.voice_channels.count()
        return format_html('<span class="badge bg-info">{} text</span> <span class="badge bg-primary">{} voice</span>', text, voice)
    channel_count.short_description = 'Channels'


@admin.register(ServerRole)
class ServerRoleAdmin(admin.ModelAdmin):
    """Admin interface for ServerRole model"""
    list_display = ('name', 'server', 'color_display', 'position', 'member_count', 'created_at')
    list_filter = ('server', 'position', 'created_at')
    search_fields = ('name', 'server__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Role Information', {
            'fields': ('server', 'name', 'color', 'position')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'description': 'JSON format: {"manage_channels": true, "manage_roles": false, ...}'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        """Display role color"""
        return format_html(
            '<div style="background-color: {}; width: 30px; height: 30px; border-radius: 4px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'
    
    def member_count(self, obj):
        """Display member count with this role"""
        return obj.members.count()
    member_count.short_description = 'Members'


@admin.register(ServerMember)
class ServerMemberAdmin(admin.ModelAdmin):
    """Admin interface for ServerMember model"""
    list_display = ('user', 'server', 'nickname', 'role_list', 'is_online', 'joined_at')
    list_filter = ('is_online', 'server', 'joined_at')
    search_fields = ('user__username', 'nickname', 'server__name')
    filter_horizontal = ('roles',)
    readonly_fields = ('joined_at',)
    
    fieldsets = (
        ('Member Information', {
            'fields': ('server', 'user', 'nickname')
        }),
        ('Roles & Status', {
            'fields': ('roles', 'is_online')
        }),
        ('Timestamps', {
            'fields': ('joined_at',),
            'classes': ('collapse',)
        }),
    )
    
    def role_list(self, obj):
        """Display roles as badges"""
        roles = obj.roles.all()
        if roles:
            badges = []
            for role in roles:
                badges.append(f'<span class="badge" style="background-color: {role.color};">{role.name}</span>')
            return format_html(' '.join(badges))
        return format_html('<span class="text-muted">No roles</span>')
    role_list.short_description = 'Roles'


@admin.register(TextChannel)
class TextChannelAdmin(admin.ModelAdmin):
    """Admin interface for TextChannel model"""
    list_display = ('name', 'server', 'position', 'message_count', 'is_private', 'created_at')
    list_filter = ('is_private', 'server', 'created_at')
    search_fields = ('name', 'slug', 'server__name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Channel Information', {
            'fields': ('server', 'name', 'slug', 'description', 'position')
        }),
        ('Settings', {
            'fields': ('is_private',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def message_count(self, obj):
        """Display message count"""
        count = obj.messages.count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    message_count.short_description = 'Messages'


@admin.register(VoiceChannel)
class VoiceChannelAdmin(admin.ModelAdmin):
    """Admin interface for VoiceChannel model"""
    list_display = ('name', 'server', 'position', 'user_limit_display', 'is_private', 'created_at')
    list_filter = ('is_private', 'server', 'created_at')
    search_fields = ('name', 'slug', 'server__name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Channel Information', {
            'fields': ('server', 'name', 'slug', 'description', 'position')
        }),
        ('Settings', {
            'fields': ('user_limit', 'is_private')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_limit_display(self, obj):
        """Display user limit"""
        if obj.user_limit == 0:
            return format_html('<span class="badge bg-success">Unlimited</span>')
        return format_html('<span class="badge bg-warning">{}</span>', obj.user_limit)
    user_limit_display.short_description = 'User Limit'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin interface for ChatMessage model"""
    list_display = ('user', 'channel', 'content_preview', 'created_at', 'edited_at')
    list_filter = ('channel__server', 'created_at', 'edited_at')
    search_fields = ('content', 'user__username', 'channel__name')
    readonly_fields = ('created_at', 'edited_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('channel', 'user', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'edited_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Display content preview"""
        preview = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return format_html('<code>{}</code>', preview)
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'channel', 'channel__server')


# ============================================================================
# AI AGENT & WORKFLOW ADMIN
# ============================================================================

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    """Admin interface for Workflow model"""
    list_display = ('name', 'version', 'category', 'is_active', 'is_public', 'execution_count', 'success_rate_display', 'created_by', 'updated_at')
    list_filter = ('is_active', 'is_public', 'category', 'created_at')
    search_fields = ('name', 'slug', 'description', 'category', 'tags')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('slug', 'created_at', 'updated_at', 'last_executed_at', 'execution_count', 'success_count', 'failure_count', 'success_rate_display')
    filter_horizontal = ()
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category', 'tags')
        }),
        ('Workflow Definition', {
            'fields': ('definition',),
            'description': 'JSON structure defining workflow steps, variables, and triggers'
        }),
        ('Settings', {
            'fields': ('version', 'is_active', 'is_public', 'created_by')
        }),
        ('Statistics', {
            'fields': ('execution_count', 'success_count', 'failure_count', 'success_rate_display', 'last_executed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        """Display success rate"""
        rate = obj.success_rate
        color = 'success' if rate >= 80 else 'warning' if rate >= 50 else 'danger'
        return format_html('<span class="badge bg-{}">{}%</span>', color, rate)
    success_rate_display.short_description = 'Success Rate'


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowExecution model"""
    list_display = ('execution_id_short', 'workflow', 'status_badge', 'triggered_by', 'agent_instance', 'duration_display', 'created_at')
    list_filter = ('status', 'workflow', 'created_at')
    search_fields = ('execution_id', 'workflow__name', 'triggered_by__username', 'error_message')
    readonly_fields = ('execution_id', 'created_at', 'duration_display', 'is_running', 'is_completed')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Execution Information', {
            'fields': ('execution_id', 'workflow', 'status', 'triggered_by', 'agent_instance')
        }),
        ('Execution State', {
            'fields': ('current_step', 'input_data', 'output_data', 'execution_state')
        }),
        ('Results', {
            'fields': ('error_message', 'error_traceback', 'execution_log'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_display'),
            'classes': ('collapse',)
        }),
    )
    
    def execution_id_short(self, obj):
        """Display short execution ID"""
        return str(obj.execution_id)[:8]
    execution_id_short.short_description = 'Execution ID'
    
    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'pending': 'secondary',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        """Display duration"""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.2f}s"
        return '-'
    duration_display.short_description = 'Duration'


@admin.register(MemoryBank)
class MemoryBankAdmin(admin.ModelAdmin):
    """Admin interface for MemoryBank model"""
    list_display = ('title_preview', 'memory_type_badge', 'agent', 'user', 'priority_badge', 'access_count', 'relevance_score', 'created_at')
    list_filter = ('memory_type', 'priority', 'agent', 'created_at')
    search_fields = ('title', 'content', 'tags', 'agent__name', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'access_count', 'last_accessed_at', 'is_expired')
    date_hierarchy = 'created_at'
    filter_horizontal = ('related_memories',)
    
    fieldsets = (
        ('Memory Information', {
            'fields': ('title', 'content', 'memory_type', 'tags', 'priority')
        }),
        ('Association', {
            'fields': ('agent', 'user')
        }),
        ('Context & Metadata', {
            'fields': ('context', 'source_type', 'source_id', 'embedding'),
            'classes': ('collapse',)
        }),
        ('Relationships', {
            'fields': ('related_memories',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('access_count', 'relevance_score', 'last_accessed_at', 'expires_at', 'is_expired'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def title_preview(self, obj):
        """Display title preview"""
        preview = obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
        return format_html('<code>{}</code>', preview)
    title_preview.short_description = 'Title'
    
    def memory_type_badge(self, obj):
        """Display memory type as badge"""
        colors = {
            'conversation': 'primary',
            'context': 'info',
            'knowledge': 'success',
            'episodic': 'warning',
            'semantic': 'secondary',
            'working': 'danger',
        }
        color = colors.get(obj.memory_type, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_memory_type_display())
    memory_type_badge.short_description = 'Type'
    
    def priority_badge(self, obj):
        """Display priority as badge"""
        colors = {1: 'secondary', 2: 'info', 3: 'warning', 4: 'danger'}
        color = colors.get(obj.priority, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_priority_display())
    priority_badge.short_description = 'Priority'


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    """Admin interface for AIAgent model"""
    list_display = ('name', 'agent_type_badge', 'status_badge', 'created_by', 'is_public', 'interaction_count', 'memory_count_display', 'updated_at')
    list_filter = ('status', 'agent_type', 'is_public', 'memory_enabled', 'created_at')
    search_fields = ('name', 'slug', 'description', 'created_by__username')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('slug', 'created_at', 'updated_at', 'last_interaction_at', 'interaction_count', 'total_tokens_used', 'memory_count_display', 'is_active')
    filter_horizontal = ('enabled_workflows',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'agent_type')
        }),
        ('Configuration', {
            'fields': ('config',),
            'description': 'JSON configuration for model, parameters, system prompts, tools, etc.'
        }),
        ('Settings', {
            'fields': ('status', 'is_public', 'created_by', 'enabled_workflows')
        }),
        ('Memory Settings', {
            'fields': ('memory_enabled', 'max_memory_entries', 'memory_retention_days')
        }),
        ('Statistics', {
            'fields': ('interaction_count', 'total_tokens_used', 'memory_count_display', 'last_interaction_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def agent_type_badge(self, obj):
        """Display agent type as badge"""
        colors = {
            'assistant': 'primary',
            'workflow_automation': 'info',
            'conversational': 'success',
            'task_orchestrator': 'warning',
            'custom': 'secondary',
        }
        color = colors.get(obj.agent_type, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_agent_type_display())
    agent_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'inactive': 'secondary',
            'active': 'success',
            'training': 'info',
            'error': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def memory_count_display(self, obj):
        """Display memory count"""
        count = obj.memory_count
        return format_html('<span class="badge bg-info">{}</span>', count)
    memory_count_display.short_description = 'Memories'
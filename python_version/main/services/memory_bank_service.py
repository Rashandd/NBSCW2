"""
Memory Bank Service
Manages AI agent memories, context, and knowledge storage
"""
import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from ..models import MemoryBank, AIAgent

logger = logging.getLogger(__name__)
User = get_user_model()


class MemoryBankService:
    """
    Service class for managing AI agent memory bank
    """
    
    @staticmethod
    def create_memory(
        title: str,
        content: str,
        memory_type: str = 'context',
        agent: Optional[AIAgent] = None,
        user: Optional[User] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: int = 2,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        expires_at: Optional[timezone.datetime] = None
    ) -> MemoryBank:
        """
        Create a new memory entry
        
        Args:
            title: Memory title
            content: Memory content
            memory_type: Type of memory (conversation, context, knowledge, etc.)
            agent: Associated AI agent
            user: Associated user
            context: Context data dictionary
            tags: List of tags
            priority: Priority level (1-4)
            source_type: Source type (e.g., 'conversation', 'workflow', 'manual')
            source_id: Source identifier
            embedding: Embedding vector for semantic search
            expires_at: Expiration datetime
        
        Returns:
            Created MemoryBank instance
        """
        memory = MemoryBank.objects.create(
            title=title,
            content=content,
            memory_type=memory_type,
            agent=agent,
            user=user,
            context=context or {},
            tags=tags or [],
            priority=priority,
            source_type=source_type,
            source_id=source_id,
            embedding=embedding,
            expires_at=expires_at
        )
        logger.info(f"Created memory: {memory.title} (type: {memory_type})")
        return memory
    
    @staticmethod
    def get_memory(memory_id: int) -> Optional[MemoryBank]:
        """Get memory by ID"""
        try:
            return MemoryBank.objects.get(id=memory_id)
        except MemoryBank.DoesNotExist:
            return None
    
    @staticmethod
    def search_memories(
        agent: Optional[AIAgent] = None,
        user: Optional[User] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search_text: Optional[str] = None,
        min_relevance: float = 0.0,
        priority: Optional[int] = None,
        limit: int = 50,
        exclude_expired: bool = True
    ) -> List[MemoryBank]:
        """
        Search memories with filters
        
        Args:
            agent: Filter by AI agent
            user: Filter by user
            memory_type: Filter by memory type
            tags: Filter by tags (memory must have all tags)
            search_text: Search in title and content
            min_relevance: Minimum relevance score
            priority: Filter by priority level
            limit: Maximum number of results
            exclude_expired: Whether to exclude expired memories
        
        Returns:
            List of MemoryBank instances, ordered by relevance and recency
        """
        queryset = MemoryBank.objects.all()
        
        if agent:
            queryset = queryset.filter(agent=agent)
        
        if user:
            queryset = queryset.filter(user=user)
        
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        if search_text:
            queryset = queryset.filter(
                Q(title__icontains=search_text) |
                Q(content__icontains=search_text)
            )
        
        if min_relevance > 0:
            queryset = queryset.filter(relevance_score__gte=min_relevance)
        
        if priority:
            queryset = queryset.filter(priority=priority)
        
        if exclude_expired:
            now = timezone.now()
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now)
            )
        
        return list(queryset.order_by('-relevance_score', '-updated_at')[:limit])
    
    @staticmethod
    def update_memory(
        memory: MemoryBank,
        title: Optional[str] = None,
        content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        relevance_score: Optional[float] = None,
        priority: Optional[int] = None
    ) -> MemoryBank:
        """
        Update a memory entry
        
        Args:
            memory: MemoryBank instance to update
            title: New title
            content: New content
            context: Updated context data
            tags: Updated tags
            relevance_score: Updated relevance score
            priority: Updated priority level
        
        Returns:
            Updated MemoryBank instance
        """
        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if context is not None:
            memory.context = context
        if tags is not None:
            memory.tags = tags
        if relevance_score is not None:
            memory.relevance_score = relevance_score
        if priority is not None:
            memory.priority = priority
        
        memory.save()
        logger.info(f"Updated memory: {memory.title} (id: {memory.id})")
        return memory
    
    @staticmethod
    def access_memory(memory: MemoryBank) -> MemoryBank:
        """
        Record memory access (increases access count and updates last accessed)
        
        Args:
            memory: MemoryBank instance
        
        Returns:
            Updated MemoryBank instance
        """
        memory.access_count += 1
        memory.last_accessed_at = timezone.now()
        memory.save(update_fields=['access_count', 'last_accessed_at'])
        return memory
    
    @staticmethod
    def relate_memories(memory1: MemoryBank, memory2: MemoryBank) -> bool:
        """
        Create a relationship between two memories
        
        Args:
            memory1: First memory
            memory2: Second memory
        
        Returns:
            True if relationship created successfully
        """
        if memory1 != memory2:
            memory1.related_memories.add(memory2)
            logger.info(f"Related memory {memory1.id} to memory {memory2.id}")
            return True
        return False
    
    @staticmethod
    def get_recent_memories(
        agent: Optional[AIAgent] = None,
        user: Optional[User] = None,
        memory_type: Optional[str] = None,
        limit: int = 20
    ) -> List[MemoryBank]:
        """
        Get recently created or accessed memories
        
        Args:
            agent: Filter by AI agent
            user: Filter by user
            memory_type: Filter by memory type
            limit: Maximum number of results
        
        Returns:
            List of MemoryBank instances
        """
        queryset = MemoryBank.objects.all()
        
        if agent:
            queryset = queryset.filter(agent=agent)
        
        if user:
            queryset = queryset.filter(user=user)
        
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        
        # Order by most recently accessed or created
        return list(
            queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            ).order_by('-last_accessed_at', '-created_at')[:limit]
        )
    
    @staticmethod
    def get_conversation_history(
        agent: Optional[AIAgent] = None,
        user: Optional[User] = None,
        limit: int = 50
    ) -> List[MemoryBank]:
        """
        Get conversation history (memories of type 'conversation')
        
        Args:
            agent: Filter by AI agent
            user: Filter by user
            limit: Maximum number of results
        
        Returns:
            List of MemoryBank instances (conversations)
        """
        return MemoryBankService.search_memories(
            agent=agent,
            user=user,
            memory_type='conversation',
            limit=limit
        )
    
    @staticmethod
    def delete_memory(memory: MemoryBank):
        """Delete a memory entry"""
        memory_id = memory.id
        memory.delete()
        logger.info(f"Deleted memory: {memory_id}")
    
    @staticmethod
    def cleanup_expired_memories(agent: Optional[AIAgent] = None) -> int:
        """
        Delete expired memories
        
        Args:
            agent: Filter by AI agent (optional)
        
        Returns:
            Number of deleted memories
        """
        queryset = MemoryBank.objects.filter(
            expires_at__isnull=False,
            expires_at__lt=timezone.now()
        )
        
        if agent:
            queryset = queryset.filter(agent=agent)
        
        count = queryset.count()
        queryset.delete()
        
        logger.info(f"Cleaned up {count} expired memories")
        return count
    
    @staticmethod
    def enforce_memory_limits(agent: AIAgent) -> int:
        """
        Enforce memory limits for an agent by deleting oldest/least relevant memories
        
        Args:
            agent: AIAgent instance
        
        Returns:
            Number of deleted memories
        """
        if not agent.max_memory_entries:
            return 0
        
        current_count = MemoryBank.objects.filter(agent=agent).count()
        
        if current_count <= agent.max_memory_entries:
            return 0
        
        # Delete oldest, least relevant memories beyond limit
        excess_count = current_count - agent.max_memory_entries
        
        memories_to_delete = MemoryBank.objects.filter(agent=agent).order_by(
            'relevance_score',
            'created_at'
        )[:excess_count]
        
        count = memories_to_delete.count()
        memories_to_delete.delete()
        
        logger.info(f"Enforced memory limits for agent {agent.name}: deleted {count} memories")
        return count

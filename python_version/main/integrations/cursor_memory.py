"""
Cursor-specific Memory Bank Integration
Provides memory bank functionality optimized for Cursor AI interactions
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from ..models import MemoryBank, AIAgent
from ..services.memory_bank_service import MemoryBankService

logger = logging.getLogger(__name__)
User = get_user_model()


class CursorMemoryBank:
    """
    Cursor-specific memory bank for AI agent interactions
    Optimized for code context, conversation history, and task tracking
    """
    
    # Memory type constants
    CONVERSATION = 'conversation'
    CODE_CONTEXT = 'context'
    KNOWLEDGE = 'knowledge'
    TASK = 'episodic'
    SEMANTIC = 'semantic'
    WORKING = 'working'
    
    def __init__(self, agent: AIAgent, user: Optional[User] = None):
        """
        Initialize Cursor memory bank
        
        Args:
            agent: AIAgent instance
            user: Optional user for user-specific memories
        """
        self.agent = agent
        self.user = user
        self.service = MemoryBankService()
        logger.info(f"Initialized Cursor memory bank for agent: {agent.name}")
    
    # ========================================================================
    # Conversation Memory
    # ========================================================================
    
    def remember_conversation(
        self,
        user_message: str,
        agent_response: str,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryBank:
        """
        Store a conversation exchange
        
        Args:
            user_message: User's message
            agent_response: Agent's response
            context: Additional context (file paths, code snippets, etc.)
            tags: Tags for categorization
        
        Returns:
            Created MemoryBank instance
        """
        content = json.dumps({
            'user_message': user_message,
            'agent_response': agent_response,
            'timestamp': timezone.now().isoformat()
        }, indent=2)
        
        default_tags = ['conversation', 'cursor']
        if tags:
            default_tags.extend(tags)
        
        return self.service.create_memory(
            title=f"Conversation: {user_message[:50]}...",
            content=content,
            memory_type=self.CONVERSATION,
            agent=self.agent,
            user=self.user,
            context=context or {},
            tags=default_tags,
            priority=2,
            source_type='cursor_chat',
            source_id=None
        )
    
    def get_conversation_history(
        self,
        limit: int = 20,
        since: Optional[timezone.datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history
        
        Args:
            limit: Maximum number of conversations to retrieve
            since: Only get conversations after this datetime
        
        Returns:
            List of conversation dictionaries
        """
        memories = self.service.search_memories(
            agent=self.agent,
            user=self.user,
            memory_type=self.CONVERSATION,
            limit=limit
        )
        
        conversations = []
        for memory in memories:
            if since and memory.created_at < since:
                continue
            
            try:
                data = json.loads(memory.content)
                conversations.append({
                    'id': memory.id,
                    'user_message': data.get('user_message'),
                    'agent_response': data.get('agent_response'),
                    'timestamp': data.get('timestamp'),
                    'context': memory.context,
                    'tags': memory.tags
                })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse conversation memory {memory.id}")
        
        return conversations
    
    # ========================================================================
    # Code Context Memory
    # ========================================================================
    
    def remember_code_context(
        self,
        file_path: str,
        code_snippet: str,
        description: str,
        language: Optional[str] = None,
        line_range: Optional[Tuple[int, int]] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryBank:
        """
        Store code context for future reference
        
        Args:
            file_path: Path to the file
            code_snippet: The code snippet
            description: Description of what this code does
            language: Programming language
            line_range: Tuple of (start_line, end_line)
            tags: Tags for categorization
        
        Returns:
            Created MemoryBank instance
        """
        context_data = {
            'file_path': file_path,
            'language': language,
            'line_range': line_range,
            'type': 'code_context'
        }
        
        content = f"""File: {file_path}
Language: {language or 'Unknown'}
Lines: {line_range[0]}-{line_range[1] if line_range else 'N/A'}

Description: {description}

Code:
```{language or ''}
{code_snippet}
```"""
        
        default_tags = ['code', 'context', 'cursor']
        if language:
            default_tags.append(language)
        if tags:
            default_tags.extend(tags)
        
        return self.service.create_memory(
            title=f"Code: {file_path}",
            content=content,
            memory_type=self.CODE_CONTEXT,
            agent=self.agent,
            user=self.user,
            context=context_data,
            tags=default_tags,
            priority=2,
            source_type='code_context',
            source_id=file_path
        )
    
    def search_code_context(
        self,
        search_text: Optional[str] = None,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MemoryBank]:
        """
        Search code context memories
        
        Args:
            search_text: Text to search in content
            file_path: Filter by file path
            language: Filter by programming language
            tags: Filter by tags
            limit: Maximum results
        
        Returns:
            List of MemoryBank instances
        """
        search_tags = ['code', 'context']
        if language:
            search_tags.append(language)
        if tags:
            search_tags.extend(tags)
        
        memories = self.service.search_memories(
            agent=self.agent,
            user=self.user,
            memory_type=self.CODE_CONTEXT,
            tags=search_tags if len(search_tags) > 2 else None,
            search_text=search_text,
            limit=limit
        )
        
        # Additional filtering by file_path if provided
        if file_path:
            memories = [m for m in memories if m.context.get('file_path') == file_path]
        
        return memories
    
    # ========================================================================
    # Task/Project Memory
    # ========================================================================
    
    def remember_task(
        self,
        task_description: str,
        status: str = 'pending',
        priority: int = 2,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> MemoryBank:
        """
        Store a task or project item
        
        Args:
            task_description: Description of the task
            status: Task status (pending, in_progress, completed, cancelled)
            priority: Priority level (1-4)
            context: Additional context
            tags: Tags for categorization
        
        Returns:
            Created MemoryBank instance
        """
        task_context = {
            'status': status,
            'created_at': timezone.now().isoformat(),
            **(context or {})
        }
        
        default_tags = ['task', 'cursor', status]
        if tags:
            default_tags.extend(tags)
        
        return self.service.create_memory(
            title=f"Task: {task_description[:100]}",
            content=task_description,
            memory_type=self.TASK,
            agent=self.agent,
            user=self.user,
            context=task_context,
            tags=default_tags,
            priority=priority,
            source_type='task',
            source_id=None
        )
    
    def update_task_status(
        self,
        memory: MemoryBank,
        status: str,
        notes: Optional[str] = None
    ) -> MemoryBank:
        """
        Update task status
        
        Args:
            memory: Task memory to update
            status: New status
            notes: Optional notes about the update
        
        Returns:
            Updated MemoryBank instance
        """
        context = memory.context.copy()
        context['status'] = status
        context['updated_at'] = timezone.now().isoformat()
        
        if notes:
            if 'notes' not in context:
                context['notes'] = []
            context['notes'].append({
                'timestamp': timezone.now().isoformat(),
                'note': notes
            })
        
        # Update tags
        tags = [t for t in memory.tags if t not in ['pending', 'in_progress', 'completed', 'cancelled']]
        tags.append(status)
        
        return self.service.update_memory(
            memory=memory,
            context=context,
            tags=tags
        )
    
    def get_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        limit: int = 50
    ) -> List[MemoryBank]:
        """
        Get tasks
        
        Args:
            status: Filter by status
            priority: Filter by priority
            limit: Maximum results
        
        Returns:
            List of task memories
        """
        tags = ['task']
        if status:
            tags.append(status)
        
        return self.service.search_memories(
            agent=self.agent,
            user=self.user,
            memory_type=self.TASK,
            tags=tags,
            priority=priority,
            limit=limit
        )
    
    # ========================================================================
    # Knowledge Base
    # ========================================================================
    
    def store_knowledge(
        self,
        title: str,
        content: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: int = 2
    ) -> MemoryBank:
        """
        Store knowledge/documentation
        
        Args:
            title: Knowledge title
            content: Knowledge content
            category: Category (e.g., 'api', 'architecture', 'best-practices')
            tags: Tags for categorization
            priority: Priority level
        
        Returns:
            Created MemoryBank instance
        """
        context_data = {}
        if category:
            context_data['category'] = category
        
        default_tags = ['knowledge', 'cursor']
        if category:
            default_tags.append(category)
        if tags:
            default_tags.extend(tags)
        
        return self.service.create_memory(
            title=title,
            content=content,
            memory_type=self.KNOWLEDGE,
            agent=self.agent,
            user=self.user,
            context=context_data,
            tags=default_tags,
            priority=priority,
            source_type='knowledge_base',
            source_id=None
        )
    
    def search_knowledge(
        self,
        search_text: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MemoryBank]:
        """
        Search knowledge base
        
        Args:
            search_text: Text to search
            category: Filter by category
            tags: Filter by tags
            limit: Maximum results
        
        Returns:
            List of knowledge memories
        """
        search_tags = ['knowledge']
        if category:
            search_tags.append(category)
        if tags:
            search_tags.extend(tags)
        
        return self.service.search_memories(
            agent=self.agent,
            user=self.user,
            memory_type=self.KNOWLEDGE,
            tags=search_tags if len(search_tags) > 1 else None,
            search_text=search_text,
            limit=limit
        )
    
    # ========================================================================
    # Working Memory (Short-term)
    # ========================================================================
    
    def store_working_memory(
        self,
        title: str,
        content: str,
        expires_in_hours: int = 24,
        tags: Optional[List[str]] = None
    ) -> MemoryBank:
        """
        Store short-term working memory
        
        Args:
            title: Memory title
            content: Memory content
            expires_in_hours: Hours until expiration
            tags: Tags for categorization
        
        Returns:
            Created MemoryBank instance
        """
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        
        default_tags = ['working', 'cursor', 'temporary']
        if tags:
            default_tags.extend(tags)
        
        return self.service.create_memory(
            title=title,
            content=content,
            memory_type=self.WORKING,
            agent=self.agent,
            user=self.user,
            tags=default_tags,
            priority=1,
            expires_at=expires_at
        )
    
    # ========================================================================
    # Context Building
    # ========================================================================
    
    def build_context_for_query(
        self,
        query: str,
        include_conversation: bool = True,
        include_code: bool = True,
        include_tasks: bool = True,
        include_knowledge: bool = True,
        max_items: int = 20
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for a query
        
        Args:
            query: User query
            include_conversation: Include recent conversations
            include_code: Include relevant code context
            include_tasks: Include active tasks
            include_knowledge: Include relevant knowledge
            max_items: Maximum items per category
        
        Returns:
            Context dictionary with relevant memories
        """
        context = {
            'query': query,
            'timestamp': timezone.now().isoformat(),
            'agent': self.agent.name,
            'user': self.user.username if self.user else None
        }
        
        if include_conversation:
            context['recent_conversations'] = self.get_conversation_history(limit=5)
        
        if include_code:
            code_memories = self.search_code_context(search_text=query, limit=max_items // 4)
            context['relevant_code'] = [
                {
                    'file': m.context.get('file_path'),
                    'description': m.content.split('Description:')[1].split('Code:')[0].strip() if 'Description:' in m.content else '',
                    'relevance': m.relevance_score
                }
                for m in code_memories
            ]
        
        if include_tasks:
            active_tasks = self.get_tasks(status='in_progress', limit=max_items // 4)
            context['active_tasks'] = [
                {
                    'id': t.id,
                    'description': t.content,
                    'priority': t.priority,
                    'status': t.context.get('status')
                }
                for t in active_tasks
            ]
        
        if include_knowledge:
            knowledge = self.search_knowledge(search_text=query, limit=max_items // 4)
            context['relevant_knowledge'] = [
                {
                    'title': k.title,
                    'content': k.content[:200] + '...' if len(k.content) > 200 else k.content,
                    'category': k.context.get('category'),
                    'relevance': k.relevance_score
                }
                for k in knowledge
            ]
        
        return context
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def cleanup_expired(self) -> int:
        """
        Cleanup expired memories
        
        Returns:
            Number of deleted memories
        """
        return self.service.cleanup_expired_memories(agent=self.agent)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory statistics
        
        Returns:
            Statistics dictionary
        """
        from django.db.models import Count, Avg
        
        stats = MemoryBank.objects.filter(agent=self.agent)
        
        if self.user:
            stats = stats.filter(user=self.user)
        
        type_counts = stats.values('memory_type').annotate(count=Count('id'))
        
        return {
            'total_memories': stats.count(),
            'by_type': {item['memory_type']: item['count'] for item in type_counts},
            'average_relevance': stats.aggregate(Avg('relevance_score'))['relevance_score__avg'] or 0,
            'most_accessed': stats.order_by('-access_count').first(),
            'agent': self.agent.name,
            'user': self.user.username if self.user else None
        }

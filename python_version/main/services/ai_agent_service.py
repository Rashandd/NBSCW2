"""
AI Agent Service
Manages AI agent instances, configurations, and interactions
"""
import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from ..models import AIAgent, MemoryBank, Workflow, WorkflowExecution
from .workflow_service import WorkflowRepository
from .memory_bank_service import MemoryBankService

logger = logging.getLogger(__name__)
User = get_user_model()


class AIAgentService:
    """
    Service class for managing AI agents
    """
    
    @staticmethod
    def create_agent(
        name: str,
        agent_type: str = 'assistant',
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        created_by: Optional[User] = None,
        is_public: bool = False,
        memory_enabled: bool = True,
        max_memory_entries: int = 1000,
        memory_retention_days: Optional[int] = None
    ) -> AIAgent:
        """
        Create a new AI agent
        
        Args:
            name: Agent name
            agent_type: Type of agent (assistant, workflow_automation, etc.)
            description: Agent description
            config: Agent configuration dictionary
            created_by: User who created the agent
            is_public: Whether agent is public
            memory_enabled: Whether memory is enabled
            max_memory_entries: Maximum number of memory entries
            memory_retention_days: Memory retention period in days
        
        Returns:
            Created AIAgent instance
        """
        default_config = {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000,
            "system_prompt": "You are a helpful AI assistant.",
            "tools": ["workflow_executor", "memory_bank"],
            "parameters": {}
        }
        
        agent = AIAgent.objects.create(
            name=name,
            agent_type=agent_type,
            description=description,
            config={**default_config, **(config or {})},
            created_by=created_by,
            is_public=is_public,
            memory_enabled=memory_enabled,
            max_memory_entries=max_memory_entries,
            memory_retention_days=memory_retention_days,
            status='inactive'
        )
        
        logger.info(f"Created AI agent: {agent.name} (type: {agent_type})")
        return agent
    
    @staticmethod
    def get_agent(agent_id: Optional[int] = None, slug: Optional[str] = None) -> Optional[AIAgent]:
        """Get agent by ID or slug"""
        if agent_id:
            try:
                return AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return None
        elif slug:
            try:
                return AIAgent.objects.get(slug=slug)
            except AIAgent.DoesNotExist:
                return None
        return None
    
    @staticmethod
    def list_agents(
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        is_public: Optional[bool] = None,
        created_by: Optional[User] = None,
        search: Optional[str] = None
    ) -> List[AIAgent]:
        """
        List agents with optional filters
        
        Args:
            agent_type: Filter by agent type
            status: Filter by status
            is_public: Filter by public status
            created_by: Filter by creator
            search: Search in name, description
        
        Returns:
            List of AIAgent instances
        """
        queryset = AIAgent.objects.all()
        
        if agent_type:
            queryset = queryset.filter(agent_type=agent_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public)
        
        if created_by:
            queryset = queryset.filter(created_by=created_by)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return list(queryset.order_by('-updated_at'))
    
    @staticmethod
    def activate_agent(agent: AIAgent) -> AIAgent:
        """Activate an agent"""
        agent.status = 'active'
        agent.save(update_fields=['status'])
        logger.info(f"Activated agent: {agent.name}")
        return agent
    
    @staticmethod
    def deactivate_agent(agent: AIAgent) -> AIAgent:
        """Deactivate an agent"""
        agent.status = 'inactive'
        agent.save(update_fields=['status'])
        logger.info(f"Deactivated agent: {agent.name}")
        return agent
    
    @staticmethod
    def enable_workflow(agent: AIAgent, workflow: Workflow) -> bool:
        """Enable a workflow for an agent"""
        if workflow not in agent.enabled_workflows.all():
            agent.enabled_workflows.add(workflow)
            logger.info(f"Enabled workflow '{workflow.name}' for agent '{agent.name}'")
            return True
        return False
    
    @staticmethod
    def disable_workflow(agent: AIAgent, workflow: Workflow) -> bool:
        """Disable a workflow for an agent"""
        if workflow in agent.enabled_workflows.all():
            agent.enabled_workflows.remove(workflow)
            logger.info(f"Disabled workflow '{workflow.name}' for agent '{agent.name}'")
            return True
        return False
    
    @staticmethod
    def record_interaction(
        agent: AIAgent,
        tokens_used: int = 0,
        user: Optional[User] = None
    ) -> AIAgent:
        """
        Record an agent interaction
        
        Args:
            agent: AIAgent instance
            tokens_used: Number of tokens used
            user: User who interacted with agent
        
        Returns:
            Updated AIAgent instance
        """
        agent.interaction_count += 1
        agent.total_tokens_used += tokens_used
        agent.last_interaction_at = timezone.now()
        agent.save(update_fields=['interaction_count', 'total_tokens_used', 'last_interaction_at'])
        return agent
    
    @staticmethod
    def get_context(
        agent: AIAgent,
        user: Optional[User] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get agent context (recent memories, conversations, etc.)
        
        Args:
            agent: AIAgent instance
            user: Optional user filter
            limit: Maximum number of memories to retrieve
        
        Returns:
            Context dictionary
        """
        if not agent.memory_enabled:
            return {}
        
        # Get recent memories
        recent_memories = MemoryBankService.get_recent_memories(
            agent=agent,
            user=user,
            limit=limit
        )
        
        # Get conversation history
        conversations = MemoryBankService.get_conversation_history(
            agent=agent,
            user=user,
            limit=10
        )
        
        # Build context
        context = {
            'agent': {
                'name': agent.name,
                'type': agent.agent_type,
                'config': agent.config
            },
            'recent_memories': [
                {
                    'id': m.id,
                    'title': m.title,
                    'content': m.content,
                    'type': m.memory_type,
                    'relevance': m.relevance_score,
                    'created_at': m.created_at.isoformat()
                }
                for m in recent_memories
            ],
            'conversations': [
                {
                    'id': c.id,
                    'title': c.title,
                    'content': c.content,
                    'created_at': c.created_at.isoformat()
                }
                for c in conversations
            ],
            'stats': {
                'total_memories': agent.memory_count,
                'interactions': agent.interaction_count,
                'tokens_used': agent.total_tokens_used
            }
        }
        
        return context
    
    @staticmethod
    def execute_workflow(
        agent: AIAgent,
        workflow: Workflow,
        input_data: Dict[str, Any],
        triggered_by: Optional[User] = None
    ) -> Optional[WorkflowExecution]:
        """
        Execute a workflow using the agent
        
        Args:
            agent: AIAgent instance
            workflow: Workflow to execute
            input_data: Input data for workflow
            triggered_by: User who triggered execution
        
        Returns:
            WorkflowExecution instance or None if workflow not enabled
        """
        # Check if workflow is enabled for agent
        if workflow not in agent.enabled_workflows.all():
            logger.warning(f"Workflow '{workflow.name}' not enabled for agent '{agent.name}'")
            return None
        
        # Create execution
        execution = WorkflowRepository.execute_workflow(
            workflow=workflow,
            input_data=input_data,
            triggered_by=triggered_by,
            agent_instance=agent
        )
        
        logger.info(f"Agent '{agent.name}' executing workflow '{workflow.name}' (execution: {execution.execution_id})")
        return execution
    
    @staticmethod
    def store_memory(
        agent: AIAgent,
        title: str,
        content: str,
        memory_type: str = 'context',
        user: Optional[User] = None,
        **kwargs
    ) -> Optional[MemoryBank]:
        """
        Store a memory using the agent's memory bank
        
        Args:
            agent: AIAgent instance
            title: Memory title
            content: Memory content
            memory_type: Type of memory
            user: Associated user
            **kwargs: Additional memory parameters
        
        Returns:
            Created MemoryBank instance or None if memory disabled
        """
        if not agent.memory_enabled:
            return None
        
        # Enforce memory limits before storing
        MemoryBankService.enforce_memory_limits(agent)
        
        # Create memory
        memory = MemoryBankService.create_memory(
            title=title,
            content=content,
            memory_type=memory_type,
            agent=agent,
            user=user,
            **kwargs
        )
        
        return memory
    
    @staticmethod
    def cleanup_agent_memories(agent: AIAgent) -> Dict[str, int]:
        """
        Cleanup agent memories (expired and beyond limits)
        
        Args:
            agent: AIAgent instance
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'expired_deleted': 0,
            'limit_enforced': 0
        }
        
        # Delete expired memories
        stats['expired_deleted'] = MemoryBankService.cleanup_expired_memories(agent=agent)
        
        # Enforce memory limits
        stats['limit_enforced'] = MemoryBankService.enforce_memory_limits(agent)
        
        logger.info(f"Cleaned up memories for agent '{agent.name}': {stats}")
        return stats

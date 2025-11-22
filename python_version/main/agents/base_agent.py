"""
Base AI Agent Class
Provides base functionality for AI agents with workflow and memory integration
"""
import logging
from typing import Dict, List, Optional, Any, Callable
from django.contrib.auth import get_user_model

from ..models import AIAgent, MemoryBank, Workflow, WorkflowExecution
from ..services.ai_agent_service import AIAgentService
from ..services.memory_bank_service import MemoryBankService
from ..services.workflow_service import WorkflowRepository

logger = logging.getLogger(__name__)
User = get_user_model()


class BaseAIAgent:
    """
    Base class for AI agents with workflow and memory bank integration
    
    This class provides:
    - Memory management (store, retrieve, search)
    - Workflow execution
    - Context management
    - Interaction tracking
    """
    
    def __init__(self, agent: AIAgent):
        """
        Initialize base AI agent
        
        Args:
            agent: AIAgent model instance
        """
        if not isinstance(agent, AIAgent):
            raise ValueError("agent must be an AIAgent instance")
        
        self.agent = agent
        self.agent_service = AIAgentService()
        self.memory_service = MemoryBankService()
        self.workflow_repository = WorkflowRepository()
        
        logger.info(f"Initialized AI agent: {self.agent.name} (type: {self.agent.agent_type})")
    
    @property
    def name(self) -> str:
        """Get agent name"""
        return self.agent.name
    
    @property
    def agent_type(self) -> str:
        """Get agent type"""
        return self.agent.agent_type
    
    @property
    def is_active(self) -> bool:
        """Check if agent is active"""
        return self.agent.status == 'active'
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get agent configuration"""
        return self.agent.config
    
    # ========================================================================
    # Memory Management
    # ========================================================================
    
    def store_memory(
        self,
        title: str,
        content: str,
        memory_type: str = 'context',
        user: Optional[User] = None,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: int = 2,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> Optional[MemoryBank]:
        """
        Store a memory
        
        Args:
            title: Memory title
            content: Memory content
            memory_type: Type of memory
            user: Associated user
            context: Context data
            tags: Tags for the memory
            priority: Priority level (1-4)
            source_type: Source type
            source_id: Source identifier
        
        Returns:
            Created MemoryBank instance or None if memory disabled
        """
        if not self.agent.memory_enabled:
            logger.warning(f"Memory disabled for agent: {self.agent.name}")
            return None
        
        return self.agent_service.store_memory(
            agent=self.agent,
            title=title,
            content=content,
            memory_type=memory_type,
            user=user,
            context=context,
            tags=tags,
            priority=priority,
            source_type=source_type,
            source_id=source_id
        )
    
    def get_memory(self, memory_id: int) -> Optional[MemoryBank]:
        """Get a memory by ID"""
        memory = self.memory_service.get_memory(memory_id)
        if memory and memory.agent == self.agent:
            # Record access
            self.memory_service.access_memory(memory)
            return memory
        return None
    
    def search_memories(
        self,
        user: Optional[User] = None,
        memory_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search_text: Optional[str] = None,
        min_relevance: float = 0.0,
        priority: Optional[int] = None,
        limit: int = 50
    ) -> List[MemoryBank]:
        """
        Search memories
        
        Args:
            user: Filter by user
            memory_type: Filter by memory type
            tags: Filter by tags
            search_text: Search in title and content
            min_relevance: Minimum relevance score
            priority: Filter by priority
            limit: Maximum number of results
        
        Returns:
            List of MemoryBank instances
        """
        return self.memory_service.search_memories(
            agent=self.agent,
            user=user,
            memory_type=memory_type,
            tags=tags,
            search_text=search_text,
            min_relevance=min_relevance,
            priority=priority,
            limit=limit
        )
    
    def get_conversation_history(
        self,
        user: Optional[User] = None,
        limit: int = 50
    ) -> List[MemoryBank]:
        """
        Get conversation history
        
        Args:
            user: Filter by user
            limit: Maximum number of results
        
        Returns:
            List of conversation memories
        """
        return self.memory_service.get_conversation_history(
            agent=self.agent,
            user=user,
            limit=limit
        )
    
    def remember_conversation(
        self,
        user: User,
        user_message: str,
        agent_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[MemoryBank]:
        """
        Remember a conversation exchange
        
        Args:
            user: User who had the conversation
            user_message: User's message
            agent_response: Agent's response
            context: Additional context
        
        Returns:
            Created MemoryBank instance
        """
        content = f"User: {user_message}\n\nAgent: {agent_response}"
        title = f"Conversation with {user.username}"
        
        return self.store_memory(
            title=title,
            content=content,
            memory_type='conversation',
            user=user,
            context=context or {},
            tags=['conversation', 'interaction']
        )
    
    # ========================================================================
    # Workflow Management
    # ========================================================================
    
    def get_enabled_workflows(self) -> List[Workflow]:
        """Get list of enabled workflows for this agent"""
        return list(self.agent.enabled_workflows.filter(is_active=True))
    
    def execute_workflow(
        self,
        workflow: Workflow,
        input_data: Dict[str, Any],
        triggered_by: Optional[User] = None
    ) -> Optional[WorkflowExecution]:
        """
        Execute a workflow
        
        Args:
            workflow: Workflow to execute
            input_data: Input data for workflow
            triggered_by: User who triggered execution
        
        Returns:
            WorkflowExecution instance or None if workflow not enabled
        """
        if not self.is_active:
            logger.warning(f"Cannot execute workflow: agent '{self.agent.name}' is not active")
            return None
        
        return self.agent_service.execute_workflow(
            agent=self.agent,
            workflow=workflow,
            input_data=input_data,
            triggered_by=triggered_by
        )
    
    def execute_workflow_by_name(
        self,
        workflow_name: str,
        input_data: Dict[str, Any],
        triggered_by: Optional[User] = None
    ) -> Optional[WorkflowExecution]:
        """
        Execute a workflow by name
        
        Args:
            workflow_name: Name or slug of workflow
            input_data: Input data for workflow
            triggered_by: User who triggered execution
        
        Returns:
            WorkflowExecution instance or None if not found/not enabled
        """
        workflow = self.workflow_repository.get_workflow(slug=workflow_name)
        if not workflow:
            workflow = Workflow.objects.filter(name=workflow_name, is_active=True).first()
        
        if not workflow:
            logger.warning(f"Workflow not found: {workflow_name}")
            return None
        
        if workflow not in self.agent.enabled_workflows.all():
            logger.warning(f"Workflow '{workflow.name}' not enabled for agent '{self.agent.name}'")
            return None
        
        return self.execute_workflow(workflow, input_data, triggered_by)
    
    # ========================================================================
    # Context Management
    # ========================================================================
    
    def get_context(self, user: Optional[User] = None, limit: int = 20) -> Dict[str, Any]:
        """
        Get agent context (memories, conversations, etc.)
        
        Args:
            user: Filter by user
            limit: Maximum number of memories to include
        
        Returns:
            Context dictionary
        """
        return self.agent_service.get_context(
            agent=self.agent,
            user=user,
            limit=limit
        )
    
    # ========================================================================
    # Interaction Tracking
    # ========================================================================
    
    def record_interaction(
        self,
        tokens_used: int = 0,
        user: Optional[User] = None
    ):
        """
        Record an interaction
        
        Args:
            tokens_used: Number of tokens used
            user: User who interacted
        """
        self.agent_service.record_interaction(
            agent=self.agent,
            tokens_used=tokens_used,
            user=user
        )
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def cleanup_memories(self) -> Dict[str, int]:
        """
        Cleanup expired and excess memories
        
        Returns:
            Dictionary with cleanup statistics
        """
        return self.agent_service.cleanup_agent_memories(self.agent)
    
    def activate(self):
        """Activate the agent"""
        self.agent_service.activate_agent(self.agent)
        logger.info(f"Activated agent: {self.agent.name}")
    
    def deactivate(self):
        """Deactivate the agent"""
        self.agent_service.deactivate_agent(self.agent)
        logger.info(f"Deactivated agent: {self.agent.name}")
    
    # ========================================================================
    # Abstract/Override Methods (to be implemented by subclasses)
    # ========================================================================
    
    def process_message(
        self,
        message: str,
        user: User,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a user message and generate a response
        
        This method should be overridden by subclasses to implement
        the actual AI processing logic.
        
        Args:
            message: User message
            user: User who sent the message
            context: Additional context
        
        Returns:
            Agent response string
        
        Raises:
            NotImplementedError: If not overridden by subclass
        """
        raise NotImplementedError(
            "Subclasses must implement process_message() method"
        )
    
    def handle_workflow_completion(
        self,
        execution: WorkflowExecution,
        result: Dict[str, Any]
    ):
        """
        Handle workflow completion
        
        This method can be overridden by subclasses to handle
        workflow completion events.
        
        Args:
            execution: Completed WorkflowExecution
            result: Execution result
        """
        logger.info(f"Workflow execution completed: {execution.execution_id}")
        # Default implementation: store result in memory
        if self.agent.memory_enabled:
            self.store_memory(
                title=f"Workflow execution: {execution.workflow.name}",
                content=f"Execution ID: {execution.execution_id}\nResult: {result}",
                memory_type='episodic',
                source_type='workflow',
                source_id=str(execution.execution_id),
                tags=['workflow', 'execution']
            )
    
    def handle_workflow_error(
        self,
        execution: WorkflowExecution,
        error: Exception
    ):
        """
        Handle workflow execution error
        
        This method can be overridden by subclasses to handle
        workflow execution errors.
        
        Args:
            execution: Failed WorkflowExecution
            error: Exception that occurred
        """
        logger.error(f"Workflow execution failed: {execution.execution_id}, Error: {str(error)}")
        # Default implementation: store error in memory
        if self.agent.memory_enabled:
            self.store_memory(
                title=f"Workflow error: {execution.workflow.name}",
                content=f"Execution ID: {execution.execution_id}\nError: {str(error)}",
                memory_type='episodic',
                source_type='workflow',
                source_id=str(execution.execution_id),
                tags=['workflow', 'error'],
                priority=3  # High priority for errors
            )

"""
Workflow Repository Service
Manages workflow definitions, executions, and lifecycle
"""
import uuid
import logging
from typing import Dict, List, Optional, Any
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from ..models import Workflow, WorkflowExecution

logger = logging.getLogger(__name__)
User = get_user_model()


class WorkflowRepository:
    """
    Repository class for managing workflows and their executions
    """
    
    @staticmethod
    def create_workflow(
        name: str,
        definition: Dict[str, Any],
        description: str = "",
        category: str = "",
        tags: List[str] = None,
        version: str = "1.0.0",
        created_by: Optional[User] = None,
        is_active: bool = True,
        is_public: bool = False
    ) -> Workflow:
        """
        Create a new workflow
        
        Args:
            name: Workflow name
            definition: Workflow definition JSON
            description: Workflow description
            category: Workflow category
            tags: List of tags
            version: Version string
            created_by: User who created the workflow
            is_active: Whether workflow is active
            is_public: Whether workflow is public
        
        Returns:
            Created Workflow instance
        """
        workflow = Workflow.objects.create(
            name=name,
            definition=definition,
            description=description,
            category=category,
            tags=tags or [],
            version=version,
            created_by=created_by,
            is_active=is_active,
            is_public=is_public
        )
        logger.info(f"Created workflow: {workflow.name} (id: {workflow.id})")
        return workflow
    
    @staticmethod
    def get_workflow(workflow_id: Optional[int] = None, slug: Optional[str] = None) -> Optional[Workflow]:
        """Get workflow by ID or slug"""
        if workflow_id:
            try:
                return Workflow.objects.get(id=workflow_id, is_active=True)
            except Workflow.DoesNotExist:
                return None
        elif slug:
            try:
                return Workflow.objects.get(slug=slug, is_active=True)
            except Workflow.DoesNotExist:
                return None
        return None
    
    @staticmethod
    def list_workflows(
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
        search: Optional[str] = None
    ) -> List[Workflow]:
        """
        List workflows with optional filters
        
        Args:
            category: Filter by category
            tags: Filter by tags (workflow must have all tags)
            is_public: Filter by public status
            search: Search in name, description
        
        Returns:
            List of Workflow instances
        """
        queryset = Workflow.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])
        
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return list(queryset.order_by('-updated_at'))
    
    @staticmethod
    def execute_workflow(
        workflow: Workflow,
        input_data: Dict[str, Any],
        triggered_by: Optional[User] = None,
        agent_instance: Optional[Any] = None,
        initial_step: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow
        
        Args:
            workflow: Workflow instance to execute
            input_data: Input data for workflow
            triggered_by: User who triggered the execution
            agent_instance: AI Agent instance executing the workflow
            initial_step: Starting step (optional)
        
        Returns:
            WorkflowExecution instance
        """
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            input_data=input_data,
            triggered_by=triggered_by,
            agent_instance=agent_instance,
            status='pending',
            current_step=initial_step or (workflow.definition.get('steps', [{}])[0].get('id') if workflow.definition.get('steps') else None),
            started_at=timezone.now()
        )
        
        # Update workflow statistics
        workflow.execution_count += 1
        workflow.last_executed_at = timezone.now()
        workflow.save(update_fields=['execution_count', 'last_executed_at'])
        
        logger.info(f"Created workflow execution: {execution.execution_id} for workflow: {workflow.name}")
        return execution
    
    @staticmethod
    def update_execution_status(
        execution: WorkflowExecution,
        status: str,
        current_step: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
        execution_state: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Update workflow execution status
        
        Args:
            execution: WorkflowExecution instance
            status: New status
            current_step: Current step ID
            output_data: Output data
            execution_state: Execution state
            error_message: Error message if failed
            error_traceback: Error traceback if failed
        
        Returns:
            Updated WorkflowExecution instance
        """
        execution.status = status
        
        if current_step is not None:
            execution.current_step = current_step
        
        if output_data is not None:
            execution.output_data = output_data
        
        if execution_state is not None:
            execution.execution_state = execution_state
        
        if error_message:
            execution.error_message = error_message
        
        if error_traceback:
            execution.error_traceback = error_traceback
        
        # Update timestamps
        if status == 'running' and not execution.started_at:
            execution.started_at = timezone.now()
        elif status in ['completed', 'failed', 'cancelled']:
            execution.completed_at = timezone.now()
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds()
                execution.duration_seconds = duration
        
        execution.save()
        
        # Update workflow statistics
        if status == 'completed':
            execution.workflow.success_count += 1
            execution.workflow.save(update_fields=['success_count'])
        elif status == 'failed':
            execution.workflow.failure_count += 1
            execution.workflow.save(update_fields=['failure_count'])
        
        logger.info(f"Updated execution {execution.execution_id} status to: {status}")
        return execution
    
    @staticmethod
    def log_execution_step(
        execution: WorkflowExecution,
        step_id: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Log a step in workflow execution
        
        Args:
            execution: WorkflowExecution instance
            step_id: Step ID
            message: Log message
            data: Additional log data
        """
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'step_id': step_id,
            'message': message,
            'data': data or {}
        }
        execution.execution_log.append(log_entry)
        execution.save(update_fields=['execution_log'])
    
    @staticmethod
    def get_execution(execution_id: uuid.UUID) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID"""
        try:
            return WorkflowExecution.objects.get(execution_id=execution_id)
        except WorkflowExecution.DoesNotExist:
            return None
    
    @staticmethod
    def list_executions(
        workflow: Optional[Workflow] = None,
        triggered_by: Optional[User] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """
        List workflow executions with filters
        
        Args:
            workflow: Filter by workflow
            triggered_by: Filter by user
            status: Filter by status
            limit: Maximum number of results
        
        Returns:
            List of WorkflowExecution instances
        """
        queryset = WorkflowExecution.objects.all()
        
        if workflow:
            queryset = queryset.filter(workflow=workflow)
        
        if triggered_by:
            queryset = queryset.filter(triggered_by=triggered_by)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    @staticmethod
    def delete_workflow(workflow: Workflow):
        """Delete or deactivate a workflow"""
        workflow.is_active = False
        workflow.save(update_fields=['is_active'])
        logger.info(f"Deactivated workflow: {workflow.name}")

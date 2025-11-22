"""
API Views for AI Agent interactions
"""
import json
import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from ..models import AIAgent, Workflow, MemoryBank
from ..integrations.cursor_memory import CursorMemoryBank
from ..services.ai_agent_service import AIAgentService
from ..services.workflow_service import WorkflowRepository

logger = logging.getLogger(__name__)
User = get_user_model()


def json_response(data: Dict[str, Any], status: int = 200) -> JsonResponse:
    """Helper to create JSON response"""
    return JsonResponse(data, status=status, safe=False)


def error_response(message: str, status: int = 400) -> JsonResponse:
    """Helper to create error response"""
    return JsonResponse({'error': message}, status=status)


# ============================================================================
# Agent Endpoints
# ============================================================================

@require_http_methods(["GET"])
@login_required
def list_agents(request):
    """List available AI agents"""
    try:
        agents = AIAgentService.list_agents(
            status='active',
            is_public=True
        )
        
        return json_response({
            'agents': [
                {
                    'id': agent.id,
                    'name': agent.name,
                    'slug': agent.slug,
                    'type': agent.agent_type,
                    'description': agent.description,
                    'status': agent.status
                }
                for agent in agents
            ]
        })
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["GET"])
@login_required
def get_agent(request, agent_slug):
    """Get agent details"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        
        if not agent:
            return error_response("Agent not found", 404)
        
        return json_response({
            'id': agent.id,
            'name': agent.name,
            'slug': agent.slug,
            'type': agent.agent_type,
            'description': agent.description,
            'status': agent.status,
            'config': agent.config,
            'memory_enabled': agent.memory_enabled,
            'interaction_count': agent.interaction_count,
            'enabled_workflows': [
                {'id': w.id, 'name': w.name, 'slug': w.slug}
                for w in agent.enabled_workflows.all()
            ]
        })
    except Exception as e:
        logger.error(f"Error getting agent: {str(e)}")
        return error_response(str(e), 500)


# ============================================================================
# Memory Bank Endpoints
# ============================================================================

@require_http_methods(["POST"])
@login_required
@csrf_exempt
def store_memory(request, agent_slug):
    """Store a memory for an agent"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        if not agent:
            return error_response("Agent not found", 404)
        
        data = json.loads(request.body)
        
        cursor_memory = CursorMemoryBank(agent=agent, user=request.user)
        
        memory_type = data.get('type', 'conversation')
        
        if memory_type == 'conversation':
            memory = cursor_memory.remember_conversation(
                user_message=data.get('user_message', ''),
                agent_response=data.get('agent_response', ''),
                context=data.get('context'),
                tags=data.get('tags')
            )
        elif memory_type == 'code':
            memory = cursor_memory.remember_code_context(
                file_path=data.get('file_path', ''),
                code_snippet=data.get('code_snippet', ''),
                description=data.get('description', ''),
                language=data.get('language'),
                line_range=data.get('line_range'),
                tags=data.get('tags')
            )
        elif memory_type == 'task':
            memory = cursor_memory.remember_task(
                task_description=data.get('description', ''),
                status=data.get('status', 'pending'),
                priority=data.get('priority', 2),
                context=data.get('context'),
                tags=data.get('tags')
            )
        elif memory_type == 'knowledge':
            memory = cursor_memory.store_knowledge(
                title=data.get('title', ''),
                content=data.get('content', ''),
                category=data.get('category'),
                tags=data.get('tags'),
                priority=data.get('priority', 2)
            )
        else:
            return error_response(f"Invalid memory type: {memory_type}", 400)
        
        return json_response({
            'id': memory.id,
            'title': memory.title,
            'type': memory.memory_type,
            'created_at': memory.created_at.isoformat()
        }, 201)
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON", 400)
    except Exception as e:
        logger.error(f"Error storing memory: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["GET"])
@login_required
def search_memories(request, agent_slug):
    """Search memories for an agent"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        if not agent:
            return error_response("Agent not found", 404)
        
        cursor_memory = CursorMemoryBank(agent=agent, user=request.user)
        
        memory_type = request.GET.get('type')
        search_text = request.GET.get('q')
        tags = request.GET.getlist('tags')
        limit = int(request.GET.get('limit', 20))
        
        if memory_type == 'conversation':
            conversations = cursor_memory.get_conversation_history(limit=limit)
            return json_response({'conversations': conversations})
        
        elif memory_type == 'code':
            memories = cursor_memory.search_code_context(
                search_text=search_text,
                tags=tags if tags else None,
                limit=limit
            )
        
        elif memory_type == 'task':
            status = request.GET.get('status')
            memories = cursor_memory.get_tasks(status=status, limit=limit)
        
        elif memory_type == 'knowledge':
            memories = cursor_memory.search_knowledge(
                search_text=search_text or '',
                tags=tags if tags else None,
                limit=limit
            )
        
        else:
            # Generic search
            from ..services.memory_bank_service import MemoryBankService
            memories = MemoryBankService.search_memories(
                agent=agent,
                user=request.user,
                search_text=search_text,
                tags=tags if tags else None,
                limit=limit
            )
        
        return json_response({
            'memories': [
                {
                    'id': m.id,
                    'title': m.title,
                    'content': m.content[:200] + '...' if len(m.content) > 200 else m.content,
                    'type': m.memory_type,
                    'tags': m.tags,
                    'relevance': m.relevance_score,
                    'created_at': m.created_at.isoformat()
                }
                for m in memories
            ]
        })
        
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["GET"])
@login_required
def get_context(request, agent_slug):
    """Get comprehensive context for an agent"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        if not agent:
            return error_response("Agent not found", 404)
        
        query = request.GET.get('q', '')
        
        cursor_memory = CursorMemoryBank(agent=agent, user=request.user)
        context = cursor_memory.build_context_for_query(
            query=query,
            include_conversation=request.GET.get('conversations', 'true').lower() == 'true',
            include_code=request.GET.get('code', 'true').lower() == 'true',
            include_tasks=request.GET.get('tasks', 'true').lower() == 'true',
            include_knowledge=request.GET.get('knowledge', 'true').lower() == 'true'
        )
        
        return json_response(context)
        
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["GET"])
@login_required
def memory_statistics(request, agent_slug):
    """Get memory statistics for an agent"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        if not agent:
            return error_response("Agent not found", 404)
        
        cursor_memory = CursorMemoryBank(agent=agent, user=request.user)
        stats = cursor_memory.get_statistics()
        
        return json_response(stats)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return error_response(str(e), 500)


# ============================================================================
# Workflow Endpoints
# ============================================================================

@require_http_methods(["GET"])
@login_required
def list_workflows(request):
    """List available workflows"""
    try:
        category = request.GET.get('category')
        search = request.GET.get('q')
        
        workflows = WorkflowRepository.list_workflows(
            category=category,
            is_public=True,
            search=search
        )
        
        return json_response({
            'workflows': [
                {
                    'id': w.id,
                    'name': w.name,
                    'slug': w.slug,
                    'description': w.description,
                    'category': w.category,
                    'version': w.version,
                    'success_rate': w.success_rate
                }
                for w in workflows
            ]
        })
        
    except Exception as e:
        logger.error(f"Error listing workflows: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["POST"])
@login_required
@csrf_exempt
def execute_workflow(request, agent_slug, workflow_slug):
    """Execute a workflow using an agent"""
    try:
        agent = AIAgentService.get_agent(slug=agent_slug)
        if not agent:
            return error_response("Agent not found", 404)
        
        workflow = WorkflowRepository.get_workflow(slug=workflow_slug)
        if not workflow:
            return error_response("Workflow not found", 404)
        
        data = json.loads(request.body)
        input_data = data.get('input', {})
        
        execution = AIAgentService.execute_workflow(
            agent=agent,
            workflow=workflow,
            input_data=input_data,
            triggered_by=request.user
        )
        
        if not execution:
            return error_response("Workflow not enabled for this agent", 403)
        
        return json_response({
            'execution_id': str(execution.execution_id),
            'workflow': workflow.name,
            'status': execution.status,
            'created_at': execution.created_at.isoformat()
        }, 201)
        
    except json.JSONDecodeError:
        return error_response("Invalid JSON", 400)
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        return error_response(str(e), 500)


@require_http_methods(["GET"])
@login_required
def get_execution_status(request, execution_id):
    """Get workflow execution status"""
    try:
        import uuid
        execution = WorkflowRepository.get_execution(uuid.UUID(execution_id))
        
        if not execution:
            return error_response("Execution not found", 404)
        
        return json_response({
            'execution_id': str(execution.execution_id),
            'workflow': execution.workflow.name,
            'status': execution.status,
            'current_step': execution.current_step,
            'output_data': execution.output_data,
            'error_message': execution.error_message,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration_seconds': execution.duration_seconds
        })
        
    except ValueError:
        return error_response("Invalid execution ID", 400)
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        return error_response(str(e), 500)

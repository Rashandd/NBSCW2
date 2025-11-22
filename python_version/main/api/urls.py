"""
API URL Configuration
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Agent endpoints
    path('agents/', views.list_agents, name='list_agents'),
    path('agents/<slug:agent_slug>/', views.get_agent, name='get_agent'),
    
    # Memory bank endpoints
    path('agents/<slug:agent_slug>/memory/', views.store_memory, name='store_memory'),
    path('agents/<slug:agent_slug>/memory/search/', views.search_memories, name='search_memories'),
    path('agents/<slug:agent_slug>/context/', views.get_context, name='get_context'),
    path('agents/<slug:agent_slug>/stats/', views.memory_statistics, name='memory_statistics'),
    
    # Workflow endpoints
    path('workflows/', views.list_workflows, name='list_workflows'),
    path('agents/<slug:agent_slug>/workflows/<slug:workflow_slug>/execute/', views.execute_workflow, name='execute_workflow'),
    path('executions/<uuid:execution_id>/', views.get_execution_status, name='get_execution_status'),
]

# Examples

This directory contains example configurations for workflows and AI agents.

## Workflows

### 1. Greet User (`workflows/greet_user.json`)
Automatically greets users when they log in or join a server. Differentiates between new and returning users.

**Usage:**
```python
from main.services.workflow_service import WorkflowRepository
import json

with open('examples/workflows/greet_user.json') as f:
    workflow_def = json.load(f)

workflow = WorkflowRepository.create_workflow(
    name=workflow_def['name'],
    definition=workflow_def,
    description=workflow_def['description'],
    category=workflow_def['category']
)
```

### 2. Code Review Assistant (`workflows/code_review_assistant.json`)
Analyzes code changes and provides automated code review feedback.

**Features:**
- Syntax checking
- Style analysis
- Security scanning
- Performance suggestions

### 3. Task Tracker (`workflows/task_tracker.json`)
Tracks development tasks and sends reminders for overdue items.

**Features:**
- Active task monitoring
- Overdue task alerts
- Daily summaries
- Progress tracking

## AI Agents

### 1. Cursor Development Assistant (`agents/cursor_assistant.json`)
Specialized assistant for Cursor IDE integration with code context awareness.

**Capabilities:**
- Code explanation and documentation
- Bug detection and fixing
- Task tracking
- Context-aware suggestions

**Setup:**
```python
from main.services.ai_agent_service import AIAgentService
import json

with open('examples/agents/cursor_assistant.json') as f:
    agent_config = json.load(f)

agent = AIAgentService.create_agent(
    name=agent_config['name'],
    agent_type=agent_config['agent_type'],
    description=agent_config['description'],
    config=agent_config['config'],
    memory_enabled=agent_config['memory_enabled'],
    max_memory_entries=agent_config['max_memory_entries']
)

AIAgentService.activate_agent(agent)
```

### 2. Game Moderator Bot (`agents/game_moderator.json`)
Automated moderator for game sessions with rule enforcement.

**Features:**
- Spam detection
- Player behavior tracking
- Automatic warnings and bans
- Report handling

### 3. Community Helper (`agents/community_helper.json`)
Friendly assistant for platform navigation and community support.

**Features:**
- Platform guidance
- FAQ responses
- Troubleshooting help
- User onboarding

## Loading Examples

### Quick Load Script

Create a management command to load all examples:

```python
# main/management/commands/load_examples.py
from django.core.management.base import BaseCommand
import json
import os
from main.services.workflow_service import WorkflowRepository
from main.services.ai_agent_service import AIAgentService

class Command(BaseCommand):
    help = 'Load example workflows and agents'

    def handle(self, *args, **options):
        examples_dir = 'examples'
        
        # Load workflows
        workflows_dir = os.path.join(examples_dir, 'workflows')
        for filename in os.listdir(workflows_dir):
            if filename.endswith('.json'):
                with open(os.path.join(workflows_dir, filename)) as f:
                    data = json.load(f)
                    workflow = WorkflowRepository.create_workflow(
                        name=data['name'],
                        definition=data,
                        description=data.get('description', ''),
                        category=data.get('category', ''),
                        version=data.get('version', '1.0.0'),
                        is_public=True
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'Loaded workflow: {workflow.name}')
                    )
        
        # Load agents
        agents_dir = os.path.join(examples_dir, 'agents')
        for filename in os.listdir(agents_dir):
            if filename.endswith('.json'):
                with open(os.path.join(agents_dir, filename)) as f:
                    data = json.load(f)
                    agent = AIAgentService.create_agent(
                        name=data['name'],
                        agent_type=data['agent_type'],
                        description=data.get('description', ''),
                        config=data.get('config', {}),
                        is_public=data.get('is_public', False),
                        memory_enabled=data.get('memory_enabled', True),
                        max_memory_entries=data.get('max_memory_entries', 1000)
                    )
                    if data.get('status') == 'active':
                        AIAgentService.activate_agent(agent)
                    self.stdout.write(
                        self.style.SUCCESS(f'Loaded agent: {agent.name}')
                    )
```

Then run:
```bash
python manage.py load_examples
```

## Customization

Feel free to modify these examples to fit your needs:

1. **Workflows**: Adjust steps, conditions, and actions
2. **Agents**: Modify system prompts, parameters, and capabilities
3. **Create New**: Use these as templates for your own workflows and agents

## Testing

Test workflows and agents in the Django admin panel or via API:

```bash
# Test workflow execution
curl -X POST http://localhost:8000/api/agents/cursor-assistant/workflows/greet-user/execute/ \
  -H "Content-Type: application/json" \
  -d '{"input": {"user_id": 1}}'

# Test agent memory
curl -X POST http://localhost:8000/api/agents/cursor-assistant/memory/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "conversation",
    "user_message": "Hello!",
    "agent_response": "Hi! How can I help you today?",
    "tags": ["greeting"]
  }'
```

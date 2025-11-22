# AI Agents & Memory Bank

Complete guide to the AI agent system, workflow repository, and memory bank features.

## Overview

The AI agent system provides:
- **AI Agents**: Configurable AI assistants with different capabilities
- **Memory Bank**: Persistent memory storage with semantic search
- **Workflow Repository**: Define and execute automated workflows
- **Cursor Integration**: Specialized memory bank for Cursor IDE

## Quick Start

### Creating an AI Agent

```python
from main.services.ai_agent_service import AIAgentService

agent = AIAgentService.create_agent(
    name="My Assistant",
    agent_type="assistant",
    description="A helpful AI assistant",
    config={
        "model": "gpt-4",
        "temperature": 0.7,
        "system_prompt": "You are a helpful assistant."
    },
    memory_enabled=True
)

AIAgentService.activate_agent(agent)
```

### Using the Memory Bank

```python
from main.integrations.cursor_memory import CursorMemoryBank

memory_bank = CursorMemoryBank(agent=agent, user=user)

# Store conversation
memory_bank.remember_conversation(
    user_message="How do I implement auth?",
    agent_response="Here's how...",
    tags=['authentication']
)

# Store code context
memory_bank.remember_code_context(
    file_path="views.py",
    code_snippet="def login(request): ...",
    description="Login view",
    language="python"
)

# Search memories
memories = memory_bank.search_code_context(
    search_text="authentication",
    language="python"
)
```

## API Reference

### Agent Endpoints

**List Agents**
```http
GET /api/agents/
```

**Get Agent Details**
```http
GET /api/agents/{slug}/
```

### Memory Endpoints

**Store Memory**
```http
POST /api/agents/{slug}/memory/
Content-Type: application/json

{
  "type": "conversation",
  "user_message": "...",
  "agent_response": "...",
  "tags": ["tag1", "tag2"]
}
```

**Search Memories**
```http
GET /api/agents/{slug}/memory/search/?type=code&q=auth&limit=10
```

**Get Context**
```http
GET /api/agents/{slug}/context/?q=current+task
```

### Workflow Endpoints

**Execute Workflow**
```http
POST /api/agents/{slug}/workflows/{workflow_slug}/execute/
Content-Type: application/json

{
  "input": {
    "param1": "value1"
  }
}
```

## Models

### AIAgent
- Configurable AI agent instances
- Multiple agent types (assistant, workflow_automation, conversational)
- Status management (active, inactive, training, error)
- Memory settings and workflow enablement

### MemoryBank
- Various memory types (conversation, context, knowledge, episodic, semantic, working)
- Tagging and priority system
- Access tracking and relevance scoring
- Expiration support

### Workflow
- JSON-based workflow definitions
- Execution tracking and statistics
- Version management
- Public/private workflows

### WorkflowExecution
- Execution state and logs
- Input/output data tracking
- Error handling
- Duration tracking

## Examples

See the `examples/` directory for:
- Example workflows (greet_user, code_review_assistant, task_tracker)
- Example agents (cursor_assistant, game_moderator, community_helper)

Load examples:
```bash
python manage.py shell
# See examples/README.md for loading scripts
```

## Advanced Usage

### Custom Agent Implementation

```python
from main.agents.base_agent import BaseAIAgent

class MyCustomAgent(BaseAIAgent):
    def process_message(self, message: str, user: User, context: Dict = None) -> str:
        # Get relevant context
        agent_context = self.get_context(user=user, limit=20)
        
        # Your AI processing logic here
        response = self.call_llm(message, agent_context)
        
        # Store the conversation
        self.remember_conversation(user, message, response)
        
        return response
```

### Workflow Definition

```json
{
  "name": "My Workflow",
  "steps": [
    {
      "id": "step1",
      "type": "action",
      "action": "send_message",
      "params": {"message": "Hello!"}
    }
  ],
  "triggers": ["user_login"]
}
```

## Best Practices

1. **Memory Management**: Regularly cleanup expired memories
2. **Context Building**: Use relevant filters when building context
3. **Workflow Design**: Keep workflows focused and modular
4. **Agent Configuration**: Tune temperature and max_tokens for your use case
5. **Error Handling**: Implement proper error handling in custom agents

## Troubleshooting

**Memory not persisting?**
- Check that `memory_enabled=True` on the agent
- Verify database migrations are applied

**Workflow not executing?**
- Ensure workflow is enabled for the agent
- Check workflow status is 'active'
- Review execution logs for errors

**API returning 404?**
- Verify agent slug is correct
- Check that agent status is 'active'
- Ensure user is authenticated

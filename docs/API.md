# API Documentation

RESTful API documentation for Rashigo platform.

## Base URL

```
http://localhost:8000/api/
```

## Authentication

All API endpoints require authentication. Use Django session authentication or token-based authentication.

```bash
# Login first
curl -X POST http://localhost:8000/login/ \
  -d "username=user&password=pass"

# Then use session cookie for subsequent requests
```

## Endpoints

### Agents

#### List All Agents

```http
GET /api/agents/
```

**Response:**
```json
{
  "agents": [
    {
      "id": 1,
      "name": "Cursor Assistant",
      "slug": "cursor-assistant",
      "type": "assistant",
      "description": "AI assistant for Cursor IDE",
      "status": "active"
    }
  ]
}
```

#### Get Agent Details

```http
GET /api/agents/{slug}/
```

**Response:**
```json
{
  "id": 1,
  "name": "Cursor Assistant",
  "slug": "cursor-assistant",
  "type": "assistant",
  "description": "AI assistant for Cursor IDE",
  "status": "active",
  "config": {
    "model": "gpt-4",
    "temperature": 0.7
  },
  "memory_enabled": true,
  "interaction_count": 150,
  "enabled_workflows": [
    {"id": 1, "name": "Code Review", "slug": "code-review"}
  ]
}
```

### Memory Bank

#### Store Memory

```http
POST /api/agents/{slug}/memory/
Content-Type: application/json
```

**Request Body (Conversation):**
```json
{
  "type": "conversation",
  "user_message": "How do I implement authentication?",
  "agent_response": "Here's how to implement Django authentication...",
  "context": {"file": "views.py"},
  "tags": ["authentication", "django"]
}
```

**Request Body (Code Context):**
```json
{
  "type": "code",
  "file_path": "main/views.py",
  "code_snippet": "def login_view(request): ...",
  "description": "User login view implementation",
  "language": "python",
  "line_range": [45, 60],
  "tags": ["authentication", "views"]
}
```

**Request Body (Task):**
```json
{
  "type": "task",
  "description": "Implement password reset functionality",
  "status": "in_progress",
  "priority": 3,
  "context": {"deadline": "2025-01-15"},
  "tags": ["authentication", "feature"]
}
```

**Request Body (Knowledge):**
```json
{
  "type": "knowledge",
  "title": "Django Authentication Best Practices",
  "content": "Always use Django's built-in authentication...",
  "category": "best-practices",
  "tags": ["django", "security"],
  "priority": 2
}
```

**Response:**
```json
{
  "id": 123,
  "title": "Conversation: How do I implement...",
  "type": "conversation",
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### Search Memories

```http
GET /api/agents/{slug}/memory/search/
```

**Query Parameters:**
- `type` - Memory type (conversation, code, task, knowledge)
- `q` - Search text
- `tags` - Filter by tags (can be multiple)
- `status` - Task status (for type=task)
- `limit` - Maximum results (default: 20)

**Examples:**
```bash
# Search conversations
GET /api/agents/cursor-assistant/memory/search/?type=conversation&q=authentication&limit=10

# Search code
GET /api/agents/cursor-assistant/memory/search/?type=code&q=login&tags=python

# Get tasks
GET /api/agents/cursor-assistant/memory/search/?type=task&status=in_progress
```

**Response:**
```json
{
  "memories": [
    {
      "id": 123,
      "title": "Code: main/views.py",
      "content": "File: main/views.py...",
      "type": "code",
      "tags": ["python", "authentication"],
      "relevance": 0.95,
      "created_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

#### Get Context

```http
GET /api/agents/{slug}/context/
```

**Query Parameters:**
- `q` - Query text
- `conversations` - Include conversations (true/false)
- `code` - Include code context (true/false)
- `tasks` - Include tasks (true/false)
- `knowledge` - Include knowledge (true/false)

**Example:**
```bash
GET /api/agents/cursor-assistant/context/?q=authentication&conversations=true&code=true
```

**Response:**
```json
{
  "query": "authentication",
  "timestamp": "2025-01-01T12:00:00Z",
  "agent": "Cursor Assistant",
  "user": "john_doe",
  "recent_conversations": [
    {
      "user_message": "How do I...",
      "agent_response": "Here's how...",
      "timestamp": "2025-01-01T11:30:00Z"
    }
  ],
  "relevant_code": [
    {
      "file": "main/views.py",
      "description": "Login view implementation",
      "relevance": 0.95
    }
  ],
  "active_tasks": [
    {
      "id": 45,
      "description": "Implement password reset",
      "priority": 3,
      "status": "in_progress"
    }
  ],
  "relevant_knowledge": [
    {
      "title": "Django Auth Best Practices",
      "content": "Always use...",
      "category": "best-practices",
      "relevance": 0.88
    }
  ]
}
```

#### Memory Statistics

```http
GET /api/agents/{slug}/stats/
```

**Response:**
```json
{
  "total_memories": 1234,
  "by_type": {
    "conversation": 500,
    "code": 400,
    "task": 200,
    "knowledge": 134
  },
  "average_relevance": 0.85,
  "most_accessed": {
    "id": 123,
    "title": "Authentication Guide",
    "access_count": 45
  },
  "agent": "Cursor Assistant",
  "user": "john_doe"
}
```

### Workflows

#### List Workflows

```http
GET /api/workflows/
```

**Query Parameters:**
- `category` - Filter by category
- `q` - Search text

**Response:**
```json
{
  "workflows": [
    {
      "id": 1,
      "name": "Code Review Assistant",
      "slug": "code-review-assistant",
      "description": "Automated code review",
      "category": "development",
      "version": "1.0.0",
      "success_rate": 95.5
    }
  ]
}
```

#### Execute Workflow

```http
POST /api/agents/{agent_slug}/workflows/{workflow_slug}/execute/
Content-Type: application/json
```

**Request Body:**
```json
{
  "input": {
    "file_path": "main/views.py",
    "commit_hash": "abc123"
  }
}
```

**Response:**
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow": "Code Review Assistant",
  "status": "pending",
  "created_at": "2025-01-01T12:00:00Z"
}
```

#### Get Execution Status

```http
GET /api/executions/{execution_id}/
```

**Response:**
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "workflow": "Code Review Assistant",
  "status": "completed",
  "current_step": "step7",
  "output_data": {
    "review_comments": "Code looks good...",
    "issues_found": 2
  },
  "error_message": null,
  "started_at": "2025-01-01T12:00:00Z",
  "completed_at": "2025-01-01T12:00:15Z",
  "duration_seconds": 15.3
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message description"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

API requests are rate-limited to prevent abuse:
- 100 requests per minute per user
- 1000 requests per hour per user

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Examples

### Python

```python
import requests

# Login
session = requests.Session()
session.post('http://localhost:8000/login/', data={
    'username': 'user',
    'password': 'pass'
})

# Store memory
response = session.post(
    'http://localhost:8000/api/agents/cursor-assistant/memory/',
    json={
        'type': 'conversation',
        'user_message': 'Hello',
        'agent_response': 'Hi!',
        'tags': ['greeting']
    }
)
print(response.json())

# Search memories
response = session.get(
    'http://localhost:8000/api/agents/cursor-assistant/memory/search/',
    params={'type': 'conversation', 'limit': 10}
)
print(response.json())
```

### JavaScript

```javascript
// Store memory
fetch('http://localhost:8000/api/agents/cursor-assistant/memory/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include',
  body: JSON.stringify({
    type: 'conversation',
    user_message: 'Hello',
    agent_response: 'Hi!',
    tags: ['greeting']
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL

```bash
# Store memory
curl -X POST http://localhost:8000/api/agents/cursor-assistant/memory/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "type": "conversation",
    "user_message": "Hello",
    "agent_response": "Hi!",
    "tags": ["greeting"]
  }'

# Search memories
curl "http://localhost:8000/api/agents/cursor-assistant/memory/search/?type=conversation&limit=10" \
  -b cookies.txt
```

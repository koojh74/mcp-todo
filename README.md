# MCP Todo Server

A Model Context Protocol (MCP) server that provides todo list management functionality with Google OAuth authentication and Firestore backend.

## Features

- **Google OAuth Authentication**: Secure user authentication via Google OAuth2
- **Firestore Backend**: Persistent storage using Google Cloud Firestore
- **Bulk Operations**: Support for adding, updating, and deleting multiple todos at once
- **Rich Todo Items**: Support for due dates with hours, priority levels, and completion status
- **RESTful API**: Clean API design following MCP standards

## Setup

### Prerequisites

1. Python 3.8+
2. Google Cloud Project with Firestore enabled
3. Google OAuth2 credentials

### Environment Variables

Create a `.env` file with the following variables:

```bash
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=your_redirect_uri
```

### Installation

```bash
pip install -r requirements.txt
```

### Running the Server

```bash
python todo_main.py
```

The server will start on `http://localhost:8080`.

## API Endpoints

### Authentication

- `POST /register` - Register a new client
- `GET /authorize` - Initiate Google OAuth flow
- `POST /token` - Exchange authorization code for access token

### MCP Tools

All MCP tools are available at `/mcp` endpoint via Server-Sent Events (SSE).

#### `get_todos`
Get all todos for the authenticated user.

**Returns:**
```json
[
  {
    "id": "todo_id",
    "title": "Todo title",
    "completed": false,
    "priority": "medium",
    "due_date": "2024-12-25 14:30",
    "created_at": "2024-12-20T10:00:00"
  }
]
```

#### `add_todos`
Add multiple todo items at once.

**Parameters:**
- `todo_items`: List of todo items, each containing:
  - `title` (required): The title/description of the todo
  - `due_date` (optional): Due date in format YYYY-MM-DD or YYYY-MM-DD HH:MM
  - `priority` (optional): Priority level ('low', 'medium', 'high'), defaults to 'medium'

**Example:**
```json
{
  "todo_items": [
    {
      "title": "Complete project documentation",
      "due_date": "2024-12-25 17:00",
      "priority": "high"
    },
    {
      "title": "Review pull requests",
      "priority": "medium"
    }
  ]
}
```

#### `update_todos`
Update multiple todo items at once.

**Parameters:**
- `updates`: List of update operations, each containing:
  - `todo_id` (required): The ID of the todo to update
  - `title` (optional): New title
  - `completed` (optional): New completion status
  - `due_date` (optional): New due date in format YYYY-MM-DD or YYYY-MM-DD HH:MM
  - `priority` (optional): New priority level ('low', 'medium', 'high')

**Example:**
```json
{
  "updates": [
    {
      "todo_id": "abc123",
      "completed": true
    },
    {
      "todo_id": "def456",
      "title": "Updated title",
      "priority": "high"
    }
  ]
}
```

#### `delete_todos`
Delete multiple todo items at once.

**Parameters:**
- `todo_ids`: List of todo IDs to delete

**Returns:**
```json
{
  "deleted_count": 2,
  "deleted_ids": ["abc123", "def456"],
  "message": "Successfully deleted 2 todo(s)"
}
```

## Todo Item Structure

Each todo item contains:
- `id`: Unique identifier
- `title`: Todo description
- `completed`: Boolean completion status
- `priority`: Priority level ('low', 'medium', 'high')
- `due_date`: Optional due date (supports both date and datetime)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp (when applicable)

## Security

- All endpoints require valid JWT authentication tokens
- User data is isolated by Google user ID
- Firestore security rules should be configured appropriately

## Development

### Project Structure

```
mcp-todo/
├── todo_main.py       # Main FastAPI application with OAuth handling
├── todo_mcp.py        # MCP server implementation with todo operations
├── requirements.txt   # Python dependencies
├── .env              # Environment variables (not in git)
└── README.md         # This file
```

### Error Handling

The server provides descriptive error messages for:
- Missing required fields
- Todo items not found
- Authentication failures
- Firestore connection issues
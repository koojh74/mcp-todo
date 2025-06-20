"""MCP Todo functions for handling todo operations."""

import os
import uuid
import jwt
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

# from mcp.server.fastmcp.server import FastMCP, Context
from fastmcp import FastMCP, Context

from google.cloud import firestore
from database import user_db

# Create FastMCP instance
mcp = FastMCP(
    name="todo server",
    # instructions="A simple MCP server with GitHub OAuth authentication",
    host="0.0.0.0",
    port=8080,
    debug=True,
)

load_dotenv()

# global db
# Initialize Firestore client
try:
    db = firestore.Client(database='mcp-db')
    print("Firestore client initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize Firestore: {e}")
    print("Using in-memory storage as fallback")
    db = None

# In-memory storage for todos (user_id -> list of todos) - used as fallback
# todos_db: Dict[str, List[Dict[str, Any]]] = {}
# Thread lock for concurrent access to in-memory storage
# todos_lock = threading.Lock()

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")


def get_user_id(ctx):
    request = ctx.get_http_request()
    headers = request.headers
    authorization_header = headers.get('Authorization')
    access_token = authorization_header.replace('Bearer ', '')
    payload = jwt.decode(access_token, GOOGLE_CLIENT_SECRET, algorithms=["HS256"])
    user_id = payload['user_id']
    print(f'user_id: {user_id}')
    
    # Increment access count for this user
    try:
        user_db.increment_access_count(user_id)
    except Exception as e:
        print(f"Warning: Could not update access count: {e}")

    return user_id


@mcp.tool()
def get_todos(ctx: Context) -> List[Dict[str, Any]]:
    """Get all todos for the authenticated user
    
    Returns:
        List of todo items with id, title, completed status, priority, and optional due_date (YYYY-MM-DD or YYYY-MM-DD HH:MM)
    """
    user_id = get_user_id(ctx)
    
    if db:
        # Use Firestore
        try:
            todos_ref = db.collection('users').document(user_id).collection('todos')
            todos = []
            for doc in todos_ref.stream():
                todo = doc.to_dict()
                todo['id'] = doc.id
                todos.append(todo)
            return todos
        except Exception as e:
            print(f"Error fetching from Firestore: {e}")
            raise e
            # Fall back to in-memory
    
    # Use in-memory storage
    # if user_id not in todos_db:
    #     todos_db[user_id] = []
    # 
    # return todos_db[user_id]
    
    # If no Firestore, return empty list
    return []


@mcp.tool()
def add_todos(ctx: Context, todo_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add multiple todo items at once
    
    Args:
        todo_items: List of todo items, each containing:
            - title: The title/description of the todo (required)
            - due_date: Optional due date in format YYYY-MM-DD or YYYY-MM-DD HH:MM
            - priority: Optional priority level ('low', 'medium', 'high'), defaults to 'medium'
        
    Returns:
        List of created todo items
    """
    user_id = get_user_id(ctx)
    created_todos = []
    
    if db:
        # Use Firestore
        try:
            user_ref = db.collection('users').document(user_id)
            todos_collection = user_ref.collection('todos')
            
            # Batch write for better performance
            batch = db.batch()
            
            for item in todo_items:
                # Validate required fields
                if 'title' not in item:
                    raise ValueError(f"Missing required field 'title' in todo item")
                
                # Create new todo
                new_todo = {
                    "title": item['title'],
                    "completed": False,
                    "created_at": datetime.now().isoformat(),
                    "due_date": item.get('due_date', None),  # Optional field
                    "priority": item.get('priority', 'medium')  # Default to medium priority
                }
                
                todo_ref = todos_collection.document()
                batch.set(todo_ref, new_todo)
                new_todo['id'] = todo_ref.id
                created_todos.append(new_todo)
            
            # Commit batch
            batch.commit()
            return created_todos
            
        except Exception as e:
            print(f"Error adding to Firestore: {e}")
            raise e
            # Fall back to in-memory
    
    raise Exception("Firestore not available")


@mcp.tool()
def update_todos(ctx: Context, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update multiple todo items at once
    
    Args:
        updates: List of update operations, each containing:
            - todo_id: The ID of the todo to update (required)
            - title: New title (optional)
            - completed: New completion status (optional)
            - due_date: New due date in format YYYY-MM-DD or YYYY-MM-DD HH:MM (optional)
            - priority: New priority level ('low', 'medium', 'high') (optional)
        
    Returns:
        List of updated todo items
    """
    user_id = get_user_id(ctx)
    updated_todos = []
    
    if db:
        # Use Firestore
        try:
            user_ref = db.collection('users').document(user_id)
            todos_collection = user_ref.collection('todos')
            
            # Batch write for better performance
            batch = db.batch()
            
            for update in updates:
                # Validate required fields
                if 'todo_id' not in update:
                    raise ValueError(f"Missing required field 'todo_id' in update item")
                
                todo_id = update['todo_id']
                todo_ref = todos_collection.document(todo_id)
                
                # Check if todo exists
                todo = todo_ref.get()
                if not todo.exists:
                    raise ValueError(f"Todo with id {todo_id} not found")
                
                # Build update data
                update_data = {}
                if 'title' in update:
                    update_data["title"] = update['title']
                if 'completed' in update:
                    update_data["completed"] = update['completed']
                if 'due_date' in update:
                    update_data["due_date"] = update['due_date']
                if 'priority' in update:
                    update_data["priority"] = update['priority']
                update_data["updated_at"] = datetime.now().isoformat()
                
                # Add to batch
                batch.update(todo_ref, update_data)
                
                # Prepare return data
                updated_todo = todo.to_dict()
                updated_todo.update(update_data)
                updated_todo['id'] = todo_id
                updated_todos.append(updated_todo)
            
            # Commit batch
            batch.commit()
            return updated_todos
            
        except Exception as e:
            print(f"Error updating in Firestore: {e}")
            raise e
    
    raise Exception("Firestore not available")


@mcp.tool()
def delete_todos(ctx: Context, todo_ids: List[str]) -> Dict[str, Any]:
    """Delete multiple todo items at once
    
    Args:
        todo_ids: List of todo IDs to delete
        
    Returns:
        Summary of deletion results
    """
    user_id = get_user_id(ctx)
    
    if db:
        # Use Firestore
        try:
            user_ref = db.collection('users').document(user_id)
            todos_collection = user_ref.collection('todos')
            
            # Batch delete for better performance
            batch = db.batch()
            deleted_ids = []
            not_found_ids = []
            
            for todo_id in todo_ids:
                todo_ref = todos_collection.document(todo_id)
                
                # Check if todo exists
                todo = todo_ref.get()
                if todo.exists:
                    batch.delete(todo_ref)
                    deleted_ids.append(todo_id)
                else:
                    not_found_ids.append(todo_id)
            
            # Commit batch
            if deleted_ids:
                batch.commit()
            
            result = {
                "deleted_count": len(deleted_ids),
                "deleted_ids": deleted_ids,
                "message": f"Successfully deleted {len(deleted_ids)} todo(s)"
            }
            
            if not_found_ids:
                result["not_found_ids"] = not_found_ids
                result["message"] += f", {len(not_found_ids)} todo(s) not found"
            
            return result
            
        except Exception as e:
            print(f"Error deleting from Firestore: {e}")
            raise e
    
    raise Exception("Firestore not available")

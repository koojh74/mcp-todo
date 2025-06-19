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

    return user_id


@mcp.tool()
def get_todos(ctx: Context) -> List[Dict[str, Any]]:
    """Get all todos for the authenticated user
    
    Returns:
        List of todo items with id, title, completed status, and optional due_date
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
            - due_date: Optional due date in format YYYY-MM-DD
        
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
                    "due_date": item.get('due_date', None)  # Optional field
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

# def add_todo(ctx: Context, title: str, due_date: Optional[str] = None) -> Dict[str, Any]:
#     """Add a new todo item
    
#     Args:
#         title: The title/description of the todo
#         due_date: Optional due date in format YYYY-MM-DD
        
#     Returns:
#         The created todo item
#     """
#     user_id = get_user_id(ctx)
    
#     # Create new todo
#     new_todo = {
#         "title": title,
#         "completed": False,
#         "created_at": datetime.now().isoformat(),
#         "due_date": due_date
#     }
    
#     if db:
#         # Use Firestore
#         try:
#             todo_ref = db.collection('users').document(user_id).collection('todos').document()
#             todo_ref.set(new_todo)
#             new_todo['id'] = todo_ref.id
#             return new_todo
#         except Exception as e:
#             print(f"Error adding to Firestore: {e}")
#             raise e
#             # Fall back to in-memory
    
#     # Use in-memory storage
#     # if user_id not in todos_db:
#     #     todos_db[user_id] = []
#     # 
#     # new_todo["id"] = str(uuid.uuid4())
#     # todos_db[user_id].append(new_todo)
#     # 
#     # return new_todo
    
#     # If no Firestore, raise error
#     raise Exception("Firestore not available")


@mcp.tool()
def update_todo(ctx: Context, todo_id: str, title: Optional[str] = None, 
                completed: Optional[bool] = None, due_date: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing todo item
    
    Args:
        todo_id: The ID of the todo to update
        title: New title (optional)
        completed: New completion status (optional)
        due_date: New due date in format YYYY-MM-DD (optional)
        
    Returns:
        The updated todo item
    """
    user_id = get_user_id(ctx)
    
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if completed is not None:
        update_data["completed"] = completed
    if due_date is not None:
        update_data["due_date"] = due_date
    update_data["updated_at"] = datetime.now().isoformat()
    
    if db:
        # Use Firestore
        try:
            todo_ref = db.collection('users').document(user_id).collection('todos').document(todo_id)
            todo = todo_ref.get()
            if not todo.exists:
                raise ValueError(f"Todo with id {todo_id} not found")
            
            todo_ref.update(update_data)
            updated_todo = todo.to_dict()
            updated_todo.update(update_data)
            updated_todo['id'] = todo_id
            return updated_todo
        except Exception as e:
            print(f"Error updating in Firestore: {e}")
            if "not found" in str(e):
                raise
            raise e
            # Fall back to in-memory
    
    # Use in-memory storage
    # if user_id not in todos_db:
    #     raise ValueError("No todos found for user")
    # 
    # # Find the todo
    # for todo in todos_db[user_id]:
    #     if todo["id"] == todo_id:
    #         todo.update(update_data)
    #         return todo
    # 
    # raise ValueError(f"Todo with id {todo_id} not found")
    
    # If no Firestore, raise error
    raise Exception("Firestore not available")


@mcp.tool()
def delete_todo(ctx: Context, todo_id: str) -> Dict[str, str]:
    """Delete a todo item
    
    Args:
        todo_id: The ID of the todo to delete
        
    Returns:
        Success message
    """
    user_id = get_user_id(ctx)
    
    if db:
        # Use Firestore
        try:
            todo_ref = db.collection('users').document(user_id).collection('todos').document(todo_id)
            todo = todo_ref.get()
            if not todo.exists:
                raise ValueError(f"Todo with id {todo_id} not found")
            
            todo_ref.delete()
            return {"message": f"Todo {todo_id} deleted successfully"}
        except Exception as e:
            print(f"Error deleting from Firestore: {e}")
            if "not found" in str(e):
                raise
            raise e
            # Fall back to in-memory
    
    # Use in-memory storage
    # if user_id not in todos_db:
    #     raise ValueError("No todos found for user")
    # 
    # # Find and remove the todo
    # original_length = len(todos_db[user_id])
    # todos_db[user_id] = [todo for todo in todos_db[user_id] if todo["id"] != todo_id]
    # 
    # if len(todos_db[user_id]) == original_length:
    #     raise ValueError(f"Todo with id {todo_id} not found")
    # 
    # return {"message": f"Todo {todo_id} deleted successfully"}
    
    # If no Firestore, raise error
    raise Exception("Firestore not available")

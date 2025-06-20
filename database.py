"""Database module for user management using Google Firestore."""

import os
from datetime import datetime
from google.cloud import firestore
from typing import Optional, Dict, Any

db = firestore.Client(database='mcp-db')

class UserDB:
    def __init__(self):
        self.collection = db.collection('users')
    
    def get_or_create_user(self, user_id: str, email: str, name: str) -> Dict[str, Any]:
        """Get existing user or create new user with initial data."""
        user_ref = self.collection.document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_ref.update({
                'last_access': datetime.utcnow(),
                'access_count': firestore.Increment(1)
            })
            user_data['access_count'] += 1
            user_data['last_access'] = datetime.utcnow()
            return user_data
        else:
            user_data = {
                # 'user_id': user_id,
                'email': email,
                'name': name,
                'created_at': datetime.utcnow(),
                'last_access': datetime.utcnow(),
                # 'login_count': 1,
                'access_count': 0
            }
            user_ref.set(user_data)
            return user_data
    
    def increment_access_count(self, user_id: str) -> None:
        """Increment the access count for a user."""
        user_ref = self.collection.document(user_id)
        user_ref.update({
            'access_count': firestore.Increment(1),
            'last_access': datetime.utcnow()
        })
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by user_id."""
        user_doc = self.collection.document(user_id).get()
        if user_doc.exists:
            return user_doc.to_dict()
        return None

user_db = UserDB()
"""
User context utilities for the application.
This module provides functions to get the current user's ID from various contexts.
"""
from flask import g, has_request_context, current_app
from flask_jwt_extended import get_jwt_identity, get_jwt, verify_jwt_in_request


def get_current_user_id():
    """
    Get the current user ID from Flask's g object or other contexts.
    
    This function attempts to retrieve the current user ID from various sources:
    1. Flask's g object (if in a request context)
    2. Falls back to None if no user ID is available
    
    Returns:
        int: The current user ID or None if not available
    """
    try:
        # Check if we're in a request context
        if has_request_context():
            # Return user_id from Flask's g object
            return getattr(g, 'current_user_id', None)
        return None
    except Exception:
        # In case of any errors, return None
        return None

def store_user_id_in_g(user_id):
    """
    Store the user ID in Flask's g object.
    
    Args:
        user_id: The user ID to store
    """
    g.current_user_id = user_id

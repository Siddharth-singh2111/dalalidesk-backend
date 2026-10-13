"""
=== Class Description ===
This file implements the User class for authentication and authorization.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Union
import bcrypt
from datetime import datetime
from .Individual import Individual
from psql import execute_query
from Exceptions import DataError

class User(Individual):
    """
    The User class represents a system user with authentication and authorization capabilities.
    
    Attributes:
        username: The unique username for the user
        password_hash: The bcrypt hash of the user's password
        full_name: The user's full name
        email: The user's email address
        role: The user's role (admin, user, etc.)
        is_active: Whether the user account is active
        created_at: When the user was created
        last_updated: When the user was last updated
        last_updated_by: Who last updated the user
    """
    table_name = 'users'
    
    def __init__(self, username: str, password_hash: str, role: str, *args, **kwargs):
        """
        Initialize a User object.
        
        Args:
            username: The unique username for the user
            password_hash: The bcrypt hash of the user's password
            role: The user's role (admin, user, etc.)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments including:
                full_name: The user's full name
                email: The user's email address
                is_active: Whether the user account is active
                created_at: When the user was created
                last_updated: When the user was last updated
                last_updated_by: Who last updated the user
        """
        # Initialize with empty name and address since Individual requires them
        # but we don't use them for User
        super().__init__(
            name=kwargs.get('full_name', ''),
            address='',
            table_name=self.table_name,
            *args,
            **kwargs
        )
        
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.full_name = kwargs.get('full_name', '')
        self.email = kwargs.get('email', '')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.last_updated = kwargs.get('last_updated', datetime.now())
        self.last_updated_by = kwargs.get('last_updated_by', None)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: The plain text password
            
        Returns:
            str: The bcrypt hash of the password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: The plain text password to verify
            
        Returns:
            bool: True if the password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def has_permission(self, resource: str, action: str) -> bool:
        """
        Check if the user has permission to perform an action on a resource.
        
        Args:
            resource: The resource to check permissions for
            action: The action to check (create, read, update, delete)
            
        Returns:
            bool: True if the user has permission, False otherwise
        """
        if not self.is_active:
            return False

        # Admins always have full access (and reach the admin panel).
        if self.role == 'admin':
            return True

        # Map action to permission field
        action_map = {
            'create': 'can_create',
            'read': 'can_read',
            'update': 'can_update',
            'delete': 'can_delete'
        }

        if action not in action_map:
            return False

        permission_field = action_map[action]

        # Prefer per-user permissions when this user has any rows; otherwise fall
        # back to the role-based matrix so pre-existing users keep working.
        # (resource/action come from the @permission_required guards, not user input.)
        try:
            count_res = execute_query(
                f"SELECT COUNT(*) AS n FROM user_permissions WHERE user_id = {int(self.id)}"
            )
            has_user_perms = (
                count_res['status'] == 'okay' and count_res['result']
                and int(count_res['result'][0]['n']) > 0
            )
        except Exception:
            has_user_perms = False

        if has_user_perms:
            query = (
                f"SELECT {permission_field} FROM user_permissions "
                f"WHERE user_id = {int(self.id)} AND resource = '{resource}'"
            )
        else:
            query = (
                f"SELECT {permission_field} FROM permissions "
                f"WHERE role = '{self.role}' AND resource = '{resource}'"
            )

        try:
            result = execute_query(query)
            if result['status'] == 'okay' and result['result']:
                return result['result'][0][permission_field]
            return False
        except Exception:
            return False
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: The username to authenticate
            password: The password to authenticate
            
        Returns:
            Optional[User]: The authenticated user or None if authentication fails
        """
        query = f"""
        SELECT *
        FROM users
        WHERE username = '{username}' AND is_active = TRUE
        """
        
        try:
            result = execute_query(query)
            if result['status'] == 'okay' and result['result']:
                user_data = result['result'][0]
                user = cls.from_dict(user_data)
                
                if user.verify_password(password):
                    return user
            return None
        except Exception:
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: The username to look up
            
        Returns:
            Optional[User]: The user or None if not found
        """
        query = f"""
        SELECT *
        FROM users
        WHERE username = '{username}'
        """
        
        try:
            result = execute_query(query)
            if result['status'] == 'okay' and result['result']:
                return cls.from_dict(result['result'][0])
            return None
        except Exception:
            return None
    
    @classmethod
    def get_all_users(cls) -> List[User]:
        """
        Get all users.
        
        Returns:
            List[User]: A list of all users
        """
        query = """
        SELECT *
        FROM users
        ORDER BY username
        """
        
        try:
            result = execute_query(query)
            if result['status'] == 'okay' and result['result']:
                return [cls.from_dict(user_data) for user_data in result['result']]
            return []
        except Exception:
            return []
    
    @classmethod
    def from_dict(cls, obj: Dict) -> User:
        """
        Create a User instance from a dictionary.
        
        Args:
            obj: The dictionary containing user data
            
        Returns:
            User: A new User instance
        """
        return cls(
            username=obj.get('username', ''),
            password_hash=obj.get('password_hash', ''),
            role=obj.get('role', 'user'),
            id=obj.get('id'),
            full_name=obj.get('full_name', ''),
            email=obj.get('email', ''),
            is_active=obj.get('is_active', True),
            created_at=obj.get('created_at'),
            last_updated=obj.get('last_updated'),
            last_updated_by=obj.get('last_updated_by')
        )
    
    def to_dict(self, include_password: bool = False) -> Dict:
        """
        Convert the User to a dictionary.
        
        Args:
            include_password: Whether to include the password hash
            
        Returns:
            Dict: A dictionary representation of the User
        """
        user_dict = {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'last_updated_by': self.last_updated_by
        }
        
        if include_password:
            user_dict['password_hash'] = self.password_hash
            
        return user_dict
    
    @classmethod
    def create(cls, username: str, password: str, role: str, full_name: str = '', 
               email: str = '', created_by: Optional[int] = None) -> User:
        """
        Create a new user.
        
        Args:
            username: The username for the new user
            password: The password for the new user
            role: The role for the new user
            full_name: The full name for the new user
            email: The email for the new user
            created_by: The ID of the user creating this user
            
        Returns:
            User: The newly created user
            
        Raises:
            DataError: If the user could not be created
        """
        # Check if username already exists
        if cls.get_by_username(username):
            raise DataError({
                'status': 'error',
                'message': 'Username already exists',
                'input_errors': {'username': {'error': True, 'message': 'Username already exists'}}
            })
        
        # Hash the password
        password_hash = cls.hash_password(password)

        # Insert the core columns. created_by / last_updated_by are stamped
        # automatically by execute_query's audit layer when a user is in context.
        columns = ['username', 'password_hash', 'role', 'full_name', 'email', 'is_active']
        values = [
            f"'{username}'", f"'{password_hash}'", f"'{role}'",
            f"'{full_name}'", f"'{email}'", 'TRUE',
        ]

        query = f"""
        INSERT INTO users ({', '.join(columns)})
        VALUES ({', '.join(values)})
        RETURNING *
        """
        
        try:
            result = execute_query(query)
            if result['status'] == 'okay' and result['result']:
                new_user = cls.from_dict(result['result'][0])
                # Give non-admin users the default permission template so they are
                # usable right away; the admin can then adjust each checkbox.
                if role != 'admin':
                    try:
                        from API_Database import seed_default_user_permissions
                        seed_default_user_permissions(new_user.id)
                    except Exception:
                        pass
                return new_user
            raise DataError({
                'status': 'error',
                'message': 'Failed to create user',
                'input_errors': {}
            })
        except Exception as e:
            raise DataError({
                'status': 'error',
                'message': f'Error creating user: {str(e)}',
                'input_errors': {}
            })
    
    def update(self, updated_by: Optional[int] = None) -> Dict:
        """
        Update the user in the database.
        
        Args:
            updated_by: The ID of the user performing the update
            
        Returns:
            Dict: The result of the update operation
        """
        try:
            # Escape special characters in text fields to prevent SQL injection
            def escape_sql_string(value):
                if value is None:
                    return "NULL"
                return "'" + str(value).replace("'", "''") + "'"
            
            # Prepare the update fields
            update_fields = [
                f"full_name = {escape_sql_string(self.full_name)}",
                f"email = {escape_sql_string(self.email)}",
                f"role = {escape_sql_string(self.role)}",
                f"is_active = {str(self.is_active).lower()}",
                f"last_updated = CURRENT_TIMESTAMP"
            ]
            
            if updated_by:
                update_fields.append(f"last_updated_by = {updated_by}")
            
            # Add password_hash if it's not empty
            if self.password_hash:
                update_fields.append(f"password_hash = {escape_sql_string(self.password_hash)}")
            
            update_str = ', '.join(update_fields)
            
            # Execute the update query
            query = f"""
            UPDATE users
            SET {update_str}
            WHERE id = {self.id}
            RETURNING *
            """
            
            result = execute_query(query, current_user_id=updated_by)
            if result['status'] == 'okay' and result['result']:
                # Update the instance with the returned data
                updated_user = self.from_dict(result['result'][0])
                self.__dict__.update(updated_user.__dict__)
                
                return {'status': 'okay', 'message': 'User updated successfully'}
            
            # If we get here, the query executed but didn't return any rows
            # This could happen if the user doesn't exist
            return {'status': 'error', 'message': 'User not found or no changes made'}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'status': 'error', 'message': f'Error updating user: {str(e)}'}
    
    def delete(self) -> Dict:
        """
        Delete the user from the database.
        
        Returns:
            Dict: The result of the delete operation
        """
        # Instead of actually deleting, we'll just set is_active to False
        self.is_active = False
        return self.update()

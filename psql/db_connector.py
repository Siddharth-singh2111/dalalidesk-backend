import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
import os
import re
from typing import Tuple, Dict, Optional, Any
from dotenv import load_dotenv
from Exceptions import DataError
from .remote_connector import execute_remote_query
from Multiprocessing import exec_in_available_thread
load_dotenv()

def connect():
    """
    Provides a reference to the database and its cursor
    """
    mydb = psycopg2.connect(dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'))
    return mydb

def cursor(dict=False) -> Tuple:
    """
    return the cursor and db connection
    """
    database = connect()
    if dict:
        db_cursor = database.cursor(cursor_factory=RealDictCursor)
    else:
        db_cursor = database.cursor()
    return (database, db_cursor)

def add_audit_fields_to_query(query: str, query_type: str, current_user_id: Optional[int]) -> str:
    """
    Add audit trail fields (created_by, last_updated_by) to queries when a user ID is available.
    
    Args:
        query: The SQL query
        query_type: The type of query (INSERT, UPDATE)
        current_user_id: The ID of the current user
        
    Returns:
        str: The query with audit fields added if needed
    """
    if not current_user_id or query_type not in ['INSERT', 'UPDATE']:
        return query
    
    # If the table name is audit_log, don't add audit fields
    if 'audit_log' in query.lower():
        return query
    
    try:
        if query_type == 'INSERT':
            # Check if the query already includes created_by
            if 'created_by' in query.lower():
                return query
                
            # Handle INSERT with column list and VALUES
            columns_match = re.search(r'INSERT\s+INTO\s+[^\s\(]+\s*\((.+?)\)', query, re.IGNORECASE | re.DOTALL)
            values_match = re.search(r'VALUES\s*\((.+?)\)', query, re.IGNORECASE | re.DOTALL)
            
            if columns_match and values_match:
                columns_str = columns_match.group(1).strip()
                values_str = values_match.group(1).strip()
                
                # Add created_by and last_updated_by to columns and values
                new_columns = f"{columns_str}, created_by, last_updated_by"
                new_values = f"{values_str}, {current_user_id}, {current_user_id}"
                
                # Replace in the query
                new_query = re.sub(
                    r'\((.+?)\)\s*VALUES\s*\((.+?)\)',
                    f"({new_columns}) VALUES ({new_values})",
                    query,
                    flags=re.IGNORECASE | re.DOTALL
                )
                return new_query
        
        elif query_type == 'UPDATE':
            # Check if the query already includes last_updated_by
            if 'last_updated_by' in query.lower():
                return query
                
            # Find the SET clause
            set_match = re.search(r'SET\s+(.+?)(?:\s+WHERE\s+|\s*$)', query, re.IGNORECASE | re.DOTALL)
            if set_match:
                set_clause = set_match.group(1).strip()
                
                # Add last_updated_by to the SET clause
                new_set_clause = f"{set_clause}, last_updated_by = {current_user_id}"
                
                # Replace in the query
                if 'WHERE' in query.upper():
                    new_query = re.sub(
                        r'SET\s+(.+?)\s+WHERE',
                        f"SET {new_set_clause} WHERE",
                        query,
                        flags=re.IGNORECASE | re.DOTALL
                    )
                else:
                    new_query = re.sub(
                        r'SET\s+(.+?)$',
                        f"SET {new_set_clause}",
                        query,
                        flags=re.IGNORECASE | re.DOTALL
                    )
                return new_query
    
    except Exception as e:
        print(f"Error adding audit fields to query: {e}")
        # If there's an error, return the original query to avoid breaking functionality
    
    return query

def ensure_returning_id(query: str, query_type: str) -> str:
    """
    Ensure that INSERT, UPDATE, and DELETE queries have a RETURNING id clause.
    
    Args:
        query: The SQL query
        query_type: The type of query (INSERT, UPDATE, DELETE)
        
    Returns:
        str: The query with RETURNING id clause if needed
    """
    if query_type not in ['INSERT', 'UPDATE', 'DELETE']:
        return query
        
    # Check if the query already has a RETURNING clause
    if 'RETURNING' in query.upper():
        return query
        
    # Add RETURNING id clause
    if query_type == 'INSERT':
        # For INSERT queries, add RETURNING id at the end
        return f"{query} RETURNING id"
    elif query_type in ['UPDATE', 'DELETE']:
        # For UPDATE and DELETE queries, add RETURNING id at the end
        return f"{query} RETURNING id"
    

    return query

def execute_query(query: str, dictCursor: bool=True, exec_remote: bool=True, current_user_id: Optional[int]=None, **kwargs):
    """
    Executes a query and returns the result.
    
    Args:
        query: The SQL query to execute
        dictCursor: Whether to use a dictionary cursor
        exec_remote: Whether to execute the query remotely
        current_user_id: The ID of the current user (for audit trail)
        **kwargs: Additional keyword arguments
        
    Returns:
        Dict: The result of the query execution
    """
    # If current_user_id is not provided, try to get it from Flask's context
    if current_user_id is None:
        try:
            # Import here to avoid circular imports
            from flask import current_app
            if current_app:
                # Only import the function if we're in a Flask context
                from hca_backend.app import get_user_id_from_token
                current_user_id = get_user_id_from_token()
        except (ImportError, RuntimeError):
            # Not in a Flask context or couldn't import the function
            pass
    
    
    query_type = query.strip().split()[0].upper()
    if query_type == 'WITH':
        query_type = 'SELECT'
    if query_type not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']:
        raise DataError('Invalid query type')
    
    # Add audit fields to INSERT and UPDATE queries
    if query_type in ['INSERT', 'UPDATE'] and current_user_id is not None:
        query = add_audit_fields_to_query(query, query_type, current_user_id)
    
    # Ensure INSERT, UPDATE, and DELETE queries have a RETURNING id clause
    if query_type in ['INSERT', 'UPDATE', 'DELETE']:
        query = ensure_returning_id(query, query_type)
    
    try:
        (db, cur) = cursor(dictCursor)
        
        # Execute the query
        cur.execute(query)
        
        # Handle non-SELECT queries
        if query_type != 'SELECT':
            if exec_remote and os.getenv('QUERY_REMOTE') == 'true':
                exec_in_available_thread(execute_remote_query, query)

            # Get the result for RETURNING clause
            result = []
            if query_type in ['INSERT', 'UPDATE', 'DELETE']:
                result = cur.fetchall()
                
            # Record audit log for INSERT, UPDATE, DELETE
            if query_type in ['INSERT', 'UPDATE', 'DELETE'] and current_user_id is not None and result:
                try:
                    # Only import here to avoid circular imports
                    from API_Database.audit_log import record_audit_log
                    
                    # Get record ID directly from the result
                    record_id = None
                    if result and len(result) > 0:
                        if isinstance(result[0], dict):
                            record_id = result[0].get('id')
                        else:
                            for i, col in enumerate(cur.description):
                                if col.name == 'id':
                                    record_id = result[0][i]
                                    break
                    
                    # Extract table name and changes
                    table_name, _, changes = extract_audit_info(query_type, query, cur)
                    
                    # Skip audit logging for operations on the audit_log table itself to prevent infinite loops
                    if table_name and record_id and table_name.lower() != 'audit_log':
                        # Record the audit log
                        record_audit_log(
                            user_id=current_user_id,
                            table_name=table_name,
                            record_id=record_id,
                            action=query_type,
                            changes=changes
                        )
                except Exception as audit_error:
                    # Log the error but don't fail the transaction
                    print(f"Error recording audit log: {audit_error}")
                
            db.commit()
        else:
            result = cur.fetchall()
        
        db.close()
        return {'result': result, 'status': 'okay', 'message': 'Query executed successfully!'}
    except errors.ForeignKeyViolation as e:
        # Extract details from the error message if possible
        error_message = str(e)
        violating_table_match = re.search(r'on table "([^"]+)" violates foreign key constraint', error_message)
        referenced_table_match = re.search(r'is still referenced from table "([^"]+)"', error_message)
        
        violating_table = violating_table_match.group(1) if violating_table_match else "the target table"
        referenced_table = referenced_table_match.group(1) if referenced_table_match else "another table"
        
        user_friendly_message = f"Cannot perform operation on {violating_table} because it is still referenced by {referenced_table}. Please remove related entries in {referenced_table} first."
        
        print(f'Foreign Key Violation: {e}')
        raise DataError({'status': 'error', 'message': user_friendly_message})
    except Exception as e:
        print('Error executing query:', e)
        raise DataError({'status': 'error', 'message': f'Error with Query Execution: {e}'})

def extract_audit_info(query_type: str, query: str, cursor) -> Tuple[Optional[str], Optional[int], Optional[Dict[str, Any]]]:
    """
    Extract audit information from a query.
    
    Args:
        query_type: The type of query (INSERT, UPDATE, DELETE)
        query: The SQL query
        cursor: The database cursor
        
    Returns:
        Tuple: (table_name, record_id, changes)
    """
    table_name = None
    record_id = None  # This is now a placeholder, as we get record_id directly from RETURNING
    changes = None
    
    try:
        if query_type == 'INSERT':
            # Extract table name from INSERT query
            match = re.search(r'INSERT\s+INTO\s+([^\s\(]+)', query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
                # Extract values from INSERT query for changes
                try:
                    # This is a simplified approach and might not work for all INSERT queries
                    values_match = re.search(r'VALUES\s*\((.+?)\)', query, re.IGNORECASE | re.DOTALL)
                    if values_match:
                        # Handle multi-line VALUES clause
                        values_str = values_match.group(1).strip()
                        # Split by commas, but handle quoted values
                        values = []
                        current = ""
                        in_quotes = False
                        
                        for char in values_str:
                            if char == "'" and (len(current) == 0 or current[-1] != '\\'):
                                in_quotes = not in_quotes
                            
                            if char == ',' and not in_quotes:
                                values.append(current.strip())
                                current = ""
                            else:
                                current += char
                        
                        if current:
                            values.append(current.strip())
                        
                        columns_match = re.search(r'INSERT\s+INTO\s+[^\s\(]+\s*\((.+?)\)', query, re.IGNORECASE | re.DOTALL)
                        
                        if columns_match:
                            # Handle multi-line columns clause
                            columns_str = columns_match.group(1).strip()
                            # Split by commas, but handle quoted column names
                            columns = []
                            current = ""
                            in_quotes = False
                            
                            for char in columns_str:
                                if char == '"' and (len(current) == 0 or current[-1] != '\\'):
                                    in_quotes = not in_quotes
                                
                                if char == ',' and not in_quotes:
                                    columns.append(current.strip())
                                    current = ""
                                else:
                                    current += char
                            
                            if current:
                                columns.append(current.strip())
                            
                            changes = {}
                            
                            for i, col in enumerate(columns):
                                if i < len(values):
                                    # Remove quotes from column names if present
                                    col = col.strip('"')
                                    changes[col] = values[i].strip()
                except Exception as values_error:
                    print(f"Error extracting INSERT values: {values_error}")
        
        elif query_type == 'UPDATE':
            # Extract table name from UPDATE query
            match = re.search(r'UPDATE\s+([^\s]+)', query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
                
                # Extract SET clause for changes
                try:
                    set_match = re.search(r'SET\s+(.+?)\s+WHERE', query, re.IGNORECASE | re.DOTALL)
                    if set_match:
                        set_clause = set_match.group(1)
                        changes = {}
                        
                        # Split by commas, but handle quoted values
                        assignments = []
                        current = ""
                        in_quotes = False
                        
                        for char in set_clause:
                            if char == "'" and (len(current) == 0 or current[-1] != '\\'):
                                in_quotes = not in_quotes
                            
                            if char == ',' and not in_quotes:
                                assignments.append(current.strip())
                                current = ""
                            else:
                                current += char
                        
                        if current:
                            assignments.append(current.strip())
                        
                        for assignment in assignments:
                            parts = assignment.split('=', 1)
                            if len(parts) == 2:
                                col = parts[0].strip()
                                val = parts[1].strip()
                                changes[col] = val
                except Exception as set_error:
                    print(f"Error extracting UPDATE SET clause: {set_error}")
        
        elif query_type == 'DELETE':
            # Extract table name from DELETE query
            match = re.search(r'DELETE\s+FROM\s+([^\s]+)', query, re.IGNORECASE)
            if match:
                table_name = match.group(1)
    
    except Exception as e:
        print(f"Error extracting audit info: {e}")
        import traceback
        traceback.print_exc()
    
    return table_name, record_id, changes

def update():
    """Performs an update operation on the database; placeholder implementation."""
    pass

def add_stack_val(a, b):
    """Returns the sum of two values; placeholder implementation."""
    pass

def add_stack_val_multiple(a, b):
    """Returns the sum of two values; placeholder implementation."""
    pass

def add_stack(dfas):
    """Adds a stack of values; placeholder implementation."""
    pass

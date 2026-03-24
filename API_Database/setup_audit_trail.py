"""
Script to set up the audit trail and user management database schema.
"""
import os
from psql import execute_query
import bcrypt

def setup_audit_trail():
    """
    Sets up the audit trail and user management database schema.
    Creates the necessary tables and adds audit fields to existing tables.
    """
    print("Setting up audit trail and user management database schema...")
    
    # Read the SQL file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(script_dir, 'audit_trail_schema.sql')
    
    with open(sql_file_path, 'r') as file:
        sql_script = file.read()
    
    # Split the script into individual statements
    # This is a simple approach and might not work for all SQL scripts
    statements = sql_script.split(';')
    
    # Execute each statement
    for statement in statements:
        statement = statement.strip()
        if statement:
            try:
                execute_query(statement, exec_remote=False)
                print("Executed SQL statement successfully.")
            except Exception as e:
                print(f"Error executing SQL statement: {e}")
                print(f"Statement: {statement}")
    
    # Generate a proper bcrypt hash for the default admin password
    # Replace the placeholder hash in the database
    admin_password = "admin5555"  # This should be changed in production
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Replace dev placeholder or legacy fake seed hash (not a real bcrypt of any password).
    update_query = f"""
    UPDATE users 
    SET password_hash = '{password_hash}' 
    WHERE username = 'admin' 
      AND (
        password_hash LIKE '$2b$12$1xxxxxxxxxxxxxxxxxxxx%'
        OR password_hash = '$2b$12$1xxxxxxxxxxxxxxxxxxxxuZLbwxnpY0o58unSvIPxddLxGystU.'
      )
    """
    
    try:
        execute_query(update_query, exec_remote=False)
        print("Updated admin password hash.")
    except Exception as e:
        print(f"Error updating admin password hash: {e}")
    
    print("Audit trail and user management setup complete.")

if __name__ == "__main__":
    setup_audit_trail()

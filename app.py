from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import ast
import atexit  # Import atexit
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_jwt_extended import JWTManager, get_jwt
from flask_jwt_extended import create_refresh_token, verify_jwt_in_request
import base64
from functools import wraps
from pypika import Query, Table, functions as fn
from psql import execute_query
from API_Database import retrieve_indivijual, retrieve_credit, retrieve_register_entry, retrieve_memo_dalali, update_memo_dalali
from OCR.name_cache import NameMatchCache
from API_Database import insert_individual, retrieve_all, retrieve_from_id, search_entities
from API_Database import edit_individual, delete_entry, retrieve_memo_entry
from API_Database import update_register_entry, update_memo_entry
from API_Database.audit_log import search_audit_logs, get_audit_history
from backup import backup
from Entities import RegisterEntry, MemoEntry, OrderForm, Item, ItemEntry
from Individual import Supplier, Party, Bank, Transporter, User
from Reports import report_select, CustomEncoder
from Legacy_Data import add_party, add_suppliers
from Exceptions import DataError
from OCR import parse_register_entry
from OCR.ocr_queue import OCRQueue
from apscheduler.schedulers.background import BackgroundScheduler  # Import BackgroundScheduler
from background_tasks import _perform_backup # Import the backup function
ocr_queue = OCRQueue()
from utils import table_class_mapper
load_dotenv()
app = Flask(__name__)

CORS(app)

name_cache = NameMatchCache()
app.config['JSON_SORT_KEYS'] = False
app.config['JWT_SECRET_KEY'] = 'NHYd198vQNOBa9HrIAGEGNYrKHBegc9Z'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=6)
jwt = JWTManager(app)

BASE = '/api'

# --- Refactored Backup Logic is now in background_tasks.py ---

# --- Initialize Scheduler ---
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(func=_perform_backup, trigger="interval", hours=24)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Custom decorator for checking permissions
def permission_required(resource, action):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify JWT is present
            verify_jwt_in_request()
            
            # Get current user
            current_user = get_current_user()
            
            # Check if user has permission
            if not current_user or not current_user.has_permission(resource, action):
                return jsonify({
                    'status': 'error',
                    'message': 'Permission denied'
                }), 403
                
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user():
    """
    Get the current user from the JWT token.
    
    Returns:
        User: The current user or None if not authenticated
    """
    try:
        # Get the JWT identity (username)
        username = get_jwt_identity()
        if not username:
            return None
            
        # Get the user from the database
        return User.get_by_username(username)
    except Exception:
        return None

def get_current_user_id():
    """
    Get the current user ID from the JWT token.
    
    Returns:
        int: The current user ID or None if not authenticated
    """
    user = get_current_user()
    return user.id if user else None

def get_user_id_from_token():
    """
    Get the user ID directly from the JWT token claims without querying the database.
    
    Returns:
        int: The user ID from the token or None if not present/authenticated
    """
    try:
        # Verify JWT is present
        verify_jwt_in_request()
        
        # Get all claims from the token
        claims = get_jwt()
        # Return the user_id claim
        return claims.get('user_id')
    except Exception:
        # Return None if there's any error (e.g., no JWT token)
        return None

@app.route(BASE + '/login', methods=['POST'])
def login():
    """
    Authenticate a user and create JWT tokens.
    
    Returns:
        JSON: The JWT tokens and user information
    """
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    # Authenticate the user
    user = User.authenticate(username, password)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid username or password'
        }), 401
    
    # Create tokens
    access_token = create_access_token(
        identity=username,
        additional_claims={
            'role': user.role,
            'user_id': user.id
        }
    )
    refresh_token = create_refresh_token(identity=username)
    
    return jsonify({
        'status': 'okay',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role
        }
    })

@app.route(BASE + '/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """
    Refresh the JWT access token.
    
    Returns:
        JSON: The new JWT access token
    """
    # Get the current user
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'Invalid refresh token'
        }), 401
    
    # Create a new access token
    access_token = create_access_token(
        identity=current_user.username,
        additional_claims={
            'role': current_user.role,
            'user_id': current_user.id
        }
    )
    
    return jsonify({
        'status': 'okay',
        'access_token': access_token
    })

# Legacy token endpoint for backward compatibility
@app.route(BASE + '/token', methods=['POST'])
def create_token():
    """Legacy endpoint for backward compatibility."""
    return login()

@app.errorhandler(DataError)
def handle_data_error(e):
    """Handles exceptions by formatting the error into a JSON response with a 500 status code."""
    error = e.dict()
    if error['status'] == 'error' and 'input_errors' not in error:
        error['input_errors'] = {}
    print('returning error')
    print(error)
    return (jsonify(error), 500)

# User Management Endpoints

@app.route(BASE + '/users', methods=['GET'])
@jwt_required()
@permission_required('users', 'read')
def get_users():
    """
    Get all users.
    
    Returns:
        JSON: A list of all users
    """
    users = User.get_all_users()
    
    return jsonify({
        'status': 'okay',
        'users': [user.to_dict() for user in users]
    })

@app.route(BASE + '/users/<int:user_id>', methods=['GET'])
@jwt_required()
@permission_required('users', 'read')
def get_user(user_id):
    """
    Get a user by ID.
    
    Args:
        user_id: The ID of the user to get
        
    Returns:
        JSON: The user information
    """
    try:
        user = User.retrieve(user_id)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
            
        return jsonify({
            'status': 'okay',
            'user': user.to_dict()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving user: {str(e)}'
        }), 500

@app.route(BASE + '/users', methods=['POST'])
@jwt_required()
@permission_required('users', 'create')
def create_user():
    """
    Create a new user.
    
    Returns:
        JSON: The result of the create operation
    """
    try:
        data = request.json
        
        # Get the current user ID
        current_user_id = get_current_user_id()
        
        # Create the user
        user = User.create(
            username=data.get('username'),
            password=data.get('password'),
            role=data.get('role', 'user'),
            full_name=data.get('full_name', ''),
            email=data.get('email', ''),
            created_by=current_user_id
        )
        
        return jsonify({
            'status': 'okay',
            'message': 'User created successfully',
            'user': user.to_dict()
        })
    except DataError as e:
        return handle_data_error(e)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error creating user: {str(e)}'
        }), 500

@app.route(BASE + '/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@permission_required('users', 'update')
def update_user(user_id):
    """
    Update a user.
    
    Args:
        user_id: The ID of the user to update
        
    Returns:
        JSON: The result of the update operation
    """
    try:
        data = request.json
        
        # Get the user
        user = User.retrieve(user_id)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
            
        # Update the user fields
        if 'username' in data:
            user.username = data['username']
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.password_hash = User.hash_password(data['password'])
            
        # Get the current user ID
        current_user_id = get_current_user_id()
            
        # Update the user
        result = user.update(updated_by=current_user_id)
        
        if result['status'] == 'okay':
            return jsonify({
                'status': 'okay',
                'message': 'User updated successfully',
                'user': user.to_dict()
            })
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error updating user: {str(e)}'
        }), 500

@app.route(BASE + '/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
@permission_required('users', 'delete')
def delete_user(user_id):
    """
    Delete a user.
    
    Args:
        user_id: The ID of the user to delete
        
    Returns:
        JSON: The result of the delete operation
    """
    try:
        # Get the user
        user = User.retrieve(user_id)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
            
        # Get the current user ID
        current_user_id = get_current_user_id()
            
        # Delete the user
        result = user.delete()
        
        if result['status'] == 'okay':
            return jsonify({
                'status': 'okay',
                'message': 'User deleted successfully'
            })
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error deleting user: {str(e)}'
        }), 500

@app.route(BASE + '/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get the current user's profile.
    
    Returns:
        JSON: The current user's profile
    """
    # Get the current user
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
        
    return jsonify({
        'status': 'okay',
        'user': current_user.to_dict()
    })

@app.route(BASE + '/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update the current user's profile.
    
    Returns:
        JSON: The result of the update operation
    """
    try:
        data = request.json
        
        # Get the current user
        current_user = get_current_user()
        
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
            
        # Update the user fields
        if 'full_name' in data:
            current_user.full_name = data['full_name']
        if 'email' in data:
            current_user.email = data['email']
        if 'password' in data and data['password']:
            current_user.password_hash = User.hash_password(data['password'])
            
        # Update the user
        result = current_user.update(updated_by=current_user.id)
        
        if result['status'] == 'okay':
            return jsonify({
                'status': 'okay',
                'message': 'Profile updated successfully',
                'user': current_user.to_dict()
            })
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error updating profile: {str(e)}'
        }), 500

# Audit Trail Endpoints

@app.route(BASE + '/audit/history/<string:table_name>/<int:record_id>', methods=['GET'])
@jwt_required()
@permission_required('audit_log', 'read')
def get_record_audit_history(table_name, record_id):
    """
    Get the audit history for a record.
    
    Args:
        table_name: The name of the table
        record_id: The ID of the record
        
    Returns:
        JSON: The audit history
    """
    try:
        # Get pagination parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get the audit history
        result = get_audit_history(
            table_name=table_name,
            record_id=record_id,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving audit history: {str(e)}'
        }), 500

@app.route(BASE + '/audit/search', methods=['GET'])
@jwt_required()
@permission_required('audit_log', 'read')
def search_audit_trail():
    """
    Search the audit trail.
    
    Returns:
        JSON: The search results
    """
    try:
        # Get search parameters
        user_id = request.args.get('user_id', type=int)
        table_name = request.args.get('table_name')
        action = request.args.get('action')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Search the audit logs
        result = search_audit_logs(
            user_id=user_id,
            table_name=table_name,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error searching audit logs: {str(e)}'
        }), 500

@app.route(BASE + '/supplier_names_and_ids', methods=['GET'])
@jwt_required()
@permission_required('supplier', 'read')
def get_all_supplier_names():
    """Retrieves all supplier names and IDs from the database and returns them in JSON format."""
    
    # Print the full request
    print(request.args)
    data = retrieve_indivijual.get_all_names_ids('supplier')
    json_data = json.dumps(data)
    return json_data

@app.route(BASE + '/party_names_and_ids', methods=['GET'])
@jwt_required()
@permission_required('party', 'read')
def get_all_party_names():
    """Retrieves all party names and IDs from the database and returns them in JSON format."""
    data = retrieve_indivijual.get_all_names_ids('party')
    json_data = json.dumps(data)
    return json_data

@app.route(BASE + '/bank_names_and_ids', methods=['GET'])
@jwt_required()
@permission_required('bank', 'read')
def get_all_bank_names():
    """Retrieves all bank names and IDs from the database and returns them in JSON format."""
    data = retrieve_indivijual.get_all_names_ids('bank')
    json_data = json.dumps(data)
    return json_data

@app.route(BASE + '/credit/<int:supplier_id>/<int:party_id>', methods=['GET'])
@jwt_required()
@permission_required('register_entry', 'read')
def get_credit(supplier_id: int, party_id: int):
    """Fetches pending credit details for the given supplier and party and returns the data in JSON format."""
    data = retrieve_credit.get_pending_part(supplier_id, party_id)
    json_data = json.dumps(data)
    return json_data

@app.route(BASE + '/pending_bills/<int:supplier_id>/<int:party_id>', methods=['GET'])
@jwt_required()
@permission_required('register_entry', 'read')
def get_pending_bills(supplier_id: int, party_id: int):
    """Retrieves pending bill details for the specified supplier and party and returns them as JSON."""
    data = RegisterEntry.get_pending_bills(supplier_id, party_id)
    json_data = json.dumps(data)
    return json_data

@app.route(BASE + '/create_report', methods=['POST'])
@jwt_required()
@permission_required('register_entry', 'read')
def create_report():
    """Creates a report from POST data by invoking report_select.make_report and returns the report as JSON."""
    if request.method == 'POST':
        data = request.json
        report_data = report_select.make_report(data)
        return jsonify(report_data)
    return {'status': 'okay'}

@app.route(BASE + '/add/individual', methods=['POST'])
@jwt_required()
def add_individual():
    """Inserts an individual (supplier, party, bank, or transporter) into the database using provided JSON data."""
    data = request.json
    entity_mapping = {'supplier': Supplier, 'party': Party, 'bank': Bank, 'transport': Transporter}
    
    # Check permission based on entity type
    entity_type = data.get('entity')
    if not entity_type or entity_type not in entity_mapping:
        return jsonify({'status': 'error', 'message': 'Invalid entity type'}), 400
    
    # Verify JWT is present
    verify_jwt_in_request()
    
    # Get current user
    current_user = get_current_user()
    
    # Check if user has permission
    if not current_user or not current_user.has_permission(entity_type, 'create'):
        return jsonify({
            'status': 'error',
            'message': 'Permission denied'
        }), 403
    
    return entity_mapping[entity_type].insert(data)

@app.route(BASE + '/add/entry', methods=['POST'])
@jwt_required()
def add_entry():
    """Inserts an entry (register, memo, order form, item, or item entry) into the database using provided JSON data."""
    data = request.json
    entity_mapping = {'register_entry': RegisterEntry, 'memo_entry': MemoEntry, 'order_form': OrderForm, 'item': Item, 'item_entry': ItemEntry}
    
    # Check permission based on entity type
    entity_type = data.get('entity')
    if not entity_type or entity_type not in entity_mapping:
        return jsonify({'status': 'error', 'message': 'Invalid entity type'}), 400
    
    # Verify JWT is present
    verify_jwt_in_request()
    
    # Get current user
    current_user = get_current_user()
    
    # Check if user has permission
    if not current_user or not current_user.has_permission(entity_type, 'create'):
        return jsonify({
            'status': 'error',
            'message': 'Permission denied'
        }), 403
    
    return entity_mapping[entity_type].insert(data)

@app.route(BASE + '/add/register_entry', methods=['POST'])
@jwt_required()
@permission_required('register_entry', 'create')
def add_register_entry():
    """Inserts a register entry into the database using POST data and returns the insertion result."""

    data = request.json
    response = RegisterEntry.insert(data)
    return jsonify(response)

@app.route(BASE + '/add/memo_entry', methods=['POST'])
@jwt_required()
@permission_required('memo_entry', 'create')
def add_memo_entry():
    """Inserts a memo entry into the database using POST data and returns the insertion result."""
    data = request.json
    response = MemoEntry.insert(data)
    return jsonify(response)

@app.route(BASE + '/add/order_form', methods=['POST'])
@jwt_required()
@permission_required('order_form', 'create')
def add_order_form_entry():
    """Inserts an order form entry into the database using POST data and returns the insertion result."""
    data = request.json
    response = OrderForm.insert(data)
    return jsonify(response)

@app.route(BASE + '/add_legacy')
@jwt_required()
@permission_required('supplier', 'create')
def add_legacy():
    """Triggers legacy data insertion routines for suppliers and parties."""
    add_suppliers.add()
    add_party.add()
    return {'status': 'okay'}

@app.route(BASE + '/get_all', methods=['POST'])
@jwt_required()
def get_all():
    """Retrieves all records from a specified table using provided parameters and returns them in JSON format."""
    if request.method == 'POST':
        data = request.json
        
        # Check permission based on table name
        table_name = data.get('table_name')
        if not table_name:
            return jsonify({'status': 'error', 'message': 'Missing table_name parameter'}), 400
        
        # Verify JWT is present
        verify_jwt_in_request()
        
        # Get current user
        current_user = get_current_user()
        
        # Check if user has permission
        if not current_user or not current_user.has_permission(table_name, 'read'):
            return jsonify({
                'status': 'error',
                'message': 'Permission denied'
            }), 403
        
        return json.dumps(retrieve_all.get_all(**data), cls=CustomEncoder)

@app.route(BASE + '/get_by_id/<string:table_name>/<int:id>')
@jwt_required()
def get_id(table_name: str, id: int):
    """Fetches a record by ID from a specified table and returns the data in JSON format."""
    # Verify JWT is present
    verify_jwt_in_request()
    
    # Get current user
    current_user = get_current_user()
    
    # Check if user has permission
    if not current_user or not current_user.has_permission(table_name, 'read'):
        return jsonify({
            'status': 'error',
            'message': 'Permission denied'
        }), 403
    
    data = retrieve_from_id.get_from_id(table_name, id)
    return json.dumps(data)

@app.route(BASE + '/update/<string:table_name>', methods=['POST'])
@jwt_required()
def update_id(table_name: str):
    """Updates a record in a specified table with provided data and returns the update status in JSON."""
    if request.method == 'POST':
        # Verify JWT is present
        verify_jwt_in_request()
        
        # Get current user
        current_user = get_current_user()
        
        # Check if user has permission
        if not current_user or not current_user.has_permission(table_name, 'update'):
            return jsonify({
                'status': 'error',
                'message': 'Permission denied'
            }), 403
        
        data = request.json
        cls = table_class_mapper(table_name)
        instance = cls.from_dict(data)
        r_val = instance.update()
        return jsonify(r_val)

@app.route(BASE + '/delete/<string:table_name>', methods=['POST'])
@jwt_required()
def delete(table_name: str):
    """Deletes a record from a specified table based on POST data and returns the deletion status."""
    if request.method == 'POST':
        # Verify JWT is present
        verify_jwt_in_request()
        
        # Get current user
        current_user = get_current_user()
        
        # Check if user has permission
        if not current_user or not current_user.has_permission(table_name, 'delete'):
            return jsonify({
                'status': 'error',
                'message': 'Permission denied'
            }), 403
        
        data = request.json
        cls = table_class_mapper(table_name)
        instance = cls.from_dict(data, parse_memo_bills=True)
        r_val = instance.delete()
        return jsonify(r_val)
    raise DataError('Only POST requests are allowed on this /delete')

@app.route(BASE + '/get_memo_bills/<int:id>')
@jwt_required()
@permission_required('memo_entry', 'read')
def get_memo_bills(id: int):
    """Retrieves memo bills for a given ID and returns them in JSON format."""
    data = MemoEntry.get_memo_bills_by_id(id)
    return json.dumps(data)

@app.route(BASE + '/backup', methods=['GET'])
@jwt_required()
@permission_required('users', 'create')  # Using admin-level permission for backup
def backup_data():
    """Triggers the backup process manually via API.
    Returns the backup status as JSON.
    """
    print("Manual backup requested via API.")
    result = _perform_backup() # Call the imported backup logic
    status_code = 500 if result.get('status') == 'error' else 200
    return jsonify(result), status_code

@app.route(BASE + '/parse_register_entry', methods=['POST'])
@jwt_required()
@permission_required('register_entry', 'create')
def parse_register_entry_route():
    """Parse and optionally queue a register entry image."""
    try:
        if 'image' not in request.files:
            return (jsonify({'status': 'error', 'message': 'No image provided'}), 400)
        image = request.files['image']
        queue_mode = request.form.get('queue_mode', 'false').lower() == 'true'
        print(request.files)
        image_bytes = image.read()
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        if app.config.get('TESTING'):
            if queue_mode:
                return (jsonify({'supplier_name': 'Test Supplier', 'supplier_name_matched': 'Test Supplier Ltd', 'party_name': 'Test Party', 'party_name_matched': 'Test Party Inc', 'bill_number': '123', 'amount': 1000, 'date': '2024-01-29', 'queue_entry_id': 'test_queue_id'}), 200)
            else:
                return (jsonify({'supplier_name': 'Test Supplier', 'supplier_name_matched': 'Test Supplier Ltd', 'party_name': 'Test Party', 'party_name_matched': 'Test Party Inc', 'bill_number': '123', 'amount': 1000, 'date': '2024-01-29'}), 200)
        parsed_data = parse_register_entry(encoded_image, queue_mode=queue_mode)
        if parsed_data is None:
            return (jsonify({'status': 'error', 'message': 'Failed to parse image'}), 500)
        return (jsonify(parsed_data), 200)
    except Exception as e:
        print(f'Error in parse_register_entry_route: {str(e)}')
        return (jsonify({'status': 'error', 'message': f'Error processing image: {str(e)}'}), 500)

@app.route(BASE + '/get_next_ocr_entry', methods=['GET'])
@jwt_required()
@permission_required('register_entry', 'read')
def get_next_ocr_entry():
    """Get next pending OCR entry."""
    try:
        ocr_queue._verify_queue()
        entry = ocr_queue.get_next_entry()
        if entry is None:
            return (jsonify({'status': 'empty', 'message': 'No pending entries'}), 404)
        if not entry.get('ocr_data'):
            return (jsonify({'status': 'error', 'message': 'Invalid entry data'}), 500)
        return (jsonify(entry), 200)
    except Exception as e:
        print(f'Error in get_next_ocr_entry: {str(e)}')
        return (jsonify({'status': 'error', 'message': f'Error retrieving entry: {str(e)}'}), 500)

@app.route(BASE + '/mark_ocr_complete', methods=['POST'])
@jwt_required()
@permission_required('register_entry', 'update')
def mark_ocr_complete():
    """Mark OCR entry as processed."""
    try:
        data = request.json
        entry_id = data.get('entry_id')
        if not entry_id:
            return (jsonify({'status': 'error', 'message': 'Entry ID required'}), 400)
        ocr_queue.mark_complete(entry_id)
        return jsonify({'status': 'okay', 'message': 'Entry marked as processed'})
    except Exception as e:
        return (jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route(BASE + '/queue_status', methods=['GET'])
@jwt_required()
@permission_required('register_entry', 'read')
def get_queue_status():
    """Get OCR queue statistics."""
    try:
        status = ocr_queue.get_status()
        return jsonify(status)
    except Exception as e:
        return (jsonify({'status': 'error', 'message': str(e)}), 500)

@app.route(BASE + '/update_name_mapping', methods=['POST'])
@jwt_required()
@permission_required('supplier', 'update')
def update_name_mapping():
    """Update the name mapping cache with human corrections."""
    try:
        data = request.json
        original_name = data.get('original_name')
        corrected_name = data.get('corrected_name')
        entity_type = data.get('entity_type')
        if not all([original_name, corrected_name, entity_type]):
            return (jsonify({'status': 'error', 'message': 'Missing required fields'}), 400)
        if entity_type not in ['supplier', 'party']:
            return (jsonify({'status': 'error', 'message': 'Invalid entity type'}), 400)
        name_cache.update_mapping(original_name, corrected_name)
        return jsonify({'status': 'okay', 'message': 'Name mapping updated successfully'})
    except Exception as e:
        return (jsonify({'status': 'error', 'message': f'Error updating name mapping: {str(e)}'}), 500)

@app.route(BASE + '/fix_problems')
@jwt_required()
@permission_required('register_entry', 'update')
def fix():
    """Executes fix routines for register entries and returns a status message."""
    update_register_entry.fix_problems()
    return {'status': 'okay'}

@app.route(BASE + '/v2/get_by_id/<string:table_name>/<int:id>')
@jwt_required()
def get_id_v2(table_name: str, id: int):
    """Fetches a record by ID from a specified table and returns the data in JSON format with proper datetime handling."""
    # Verify JWT is present
    verify_jwt_in_request()
    
    # Get current user
    current_user = get_current_user()
    
    # Check if user has permission
    if not current_user or not current_user.has_permission(table_name, 'read'):
        return jsonify({
            'status': 'error',
            'message': 'Permission denied'
        }), 403
    
    data = retrieve_from_id.get_from_id(table_name, id)
    # Extract the first (and should be only) item from the result array
    if data and len(data) > 0:
        return json.dumps(data[0], cls=CustomEncoder)
    return json.dumps({}, cls=CustomEncoder)  # Return empty object if no data found

@app.route(BASE + '/v2/get_register_entry/<int:id>')
@jwt_required()
@permission_required('register_entry', 'read')
def get_register_entry_v2(id: int):
    """Fetches a register entry with all related data including item entries."""
    try:
        # Get basic register entry data from database
        register_entry_data = retrieve_register_entry.get_register_entry_by_id(id)
        
        # Get related item entries
        try:
            item_entries = ItemEntry.retrieve(register_entry_id=id)
            if isinstance(item_entries, list):
                register_entry_data['item_entries'] = [
                    {
                        'id': item.id,
                        'item_id': item.item_id,
                        'quantity': item.quantity,
                        'rate': item.rate,
                        'amount': item.quantity * item.rate
                    }
                    for item in item_entries
                ]
            else:
                register_entry_data['item_entries'] = [
                    {
                        'id': item_entries.id,
                        'item_id': item_entries.item_id,
                        'quantity': item_entries.quantity,
                        'rate': item_entries.rate,
                        'amount': item_entries.quantity * item_entries.rate
                    }
                ]
                
            # Get item names
            for item_entry in register_entry_data['item_entries']:
                try:
                    item = Item.retrieve_by_id(item_entry['item_id'])
                    item_entry['item_name'] = item.name
                except Exception as e:
                    print(f"Error fetching item: {str(e)}")
        except Exception as e:
            print(f"Error fetching item entries: {str(e)}")
            register_entry_data['item_entries'] = []
            
        # Get memo bills
        try:
            memo_bills_table = Table('memo_bills')
            memo_entry_table = Table('memo_entry')
            
            query = Query.from_(memo_bills_table)\
                .left_join(memo_entry_table).on(memo_bills_table.memo_id == memo_entry_table.id)\
                .select(
                    memo_bills_table.id,
                    memo_bills_table.memo_id,
                    memo_bills_table.type,
                    memo_bills_table.amount,
                    memo_entry_table.memo_number,
                    fn.ToChar(memo_entry_table.register_date, 'YYYY-MM-DD').as_('register_date')
                )\
                .where(memo_bills_table.bill_id == id)
            
            sql = query.get_sql()
            result = execute_query(sql)
            
            register_entry_data['memo_bills'] = result['result']
        except Exception as e:
            print(f"Error fetching memo bills: {str(e)}")
            register_entry_data['memo_bills'] = []
        
        return json.dumps(register_entry_data, cls=CustomEncoder)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route(BASE + '/v2/get_memo_entry/<int:id>')
@jwt_required()
@permission_required('memo_entry', 'read')
def get_memo_entry_v2(id: int):
    """Fetches a memo entry with all related data including payments and memo bills."""
    try:
        # Get memo entry data with all related information
        memo_entry_data = MemoEntry.get_memo_entry(id)
        
        # Get related register entries for memo bills
        if 'memo_bills' in memo_entry_data:
            for bill in memo_entry_data['memo_bills']:
                if bill['bill_id'] is not None:
                    try:
                        register_entry = RegisterEntry.retrieve_by_id(bill['bill_id'])
                        bill['register_entry'] = {
                            'bill_number': register_entry.bill_number,
                            'amount': register_entry.amount,
                            'register_date': register_entry.register_date.strftime('%Y-%m-%d')
                        }
                    except Exception as e:
                        print(f"Error fetching register entry: {str(e)}")
        
        return json.dumps(memo_entry_data, cls=CustomEncoder)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route(BASE + '/v2/get_next_available_memo_number')
@jwt_required()
@permission_required('memo_entry', 'read')
def get_next_available_memo_number():
    """Retrieves the next available memo number."""
    try:
        memo_number = MemoEntry.get_next_available_memo_number()
        return jsonify({'status': 'okay', "memo_number": memo_number})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route(BASE + '/memo_entries_with_dalali', methods=['GET'])
@jwt_required()
@permission_required('memo_entry', 'read')
def get_memo_entries_with_dalali():
    """Retrieves memo entries with dalali payment information, optionally filtered by date range."""
    try:
        # Get date range parameters from query string
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Get data with optional date filtering
        data = retrieve_memo_dalali.get_all_memo_entries_with_dalali(start_date, end_date)
        return json.dumps(data, cls=CustomEncoder)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route(BASE + '/update_memo_dalali', methods=['POST'])
@jwt_required()
@permission_required('memo_entry', 'update')
def update_memo_dalali_payment():
    """Updates dalali payment information for a memo entry."""
    if request.method == 'POST':
        data = request.json
        
        if 'memo_id' not in data:
            return jsonify({'status': 'error', 'message': 'Missing memo_id parameter'}), 400
        
        memo_id = data['memo_id']
        
        # If a specific field is being updated
        if 'field' in data and 'value' in data:
            field = data['field']
            value = data['value']
            result = update_memo_dalali.update_dalali_payment_field(memo_id, field, value)
        else:
            # Full update
            is_paid = data.get('is_paid', False)
            paid_amount = data.get('paid_amount', 0)
            remark = data.get('remark', '')
            result = update_memo_dalali.create_or_update_dalali_payment(memo_id, is_paid, paid_amount, remark)
        
        return jsonify(result)
    
    return jsonify({'status': 'error', 'message': 'Only POST requests are allowed'}), 405

@app.route(BASE + '/search', methods=['POST'])
@jwt_required()
def search():
    """Search for entities that match the provided search query."""
    if request.method == 'POST':
        data = request.json
        
        if 'table_name' not in data or 'search' not in data:
            return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400
            
        table_name = data['table_name']
        search_query = data['search']
        
        # Verify JWT is present
        verify_jwt_in_request()
        
        # Get current user
        current_user = get_current_user()
        
        # Check if user has permission
        if not current_user or not current_user.has_permission(table_name, 'read'):
            return jsonify({
                'status': 'error',
                'message': 'Permission denied'
            }), 403
        
        # Remove these keys so they don't interfere with additional filters
        search_data = {k: v for k, v in data.items() if k not in ['table_name', 'search']}
        
        try:
            results = search_entities.search_entities(table_name, search_query, **search_data)
            print("for table", table_name, "results are", results)
            return json.dumps(results, cls=CustomEncoder)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route(BASE + '/v2/get_all_register_entries', methods=['GET'])
@jwt_required()
@permission_required('register_entry', 'read')
def get_all_register_entries_with_names():
    """Retrieves all register entries with supplier and party names."""
    try:
        # Get pagination parameters
        page = request.args.get('page', type=int)
        page_size = request.args.get('page_size', type=int)
        
        # Get filter parameters
        filters = {}
        if request.args.get('supplier_id'):
            filters['supplier_id'] = int(request.args.get('supplier_id'))
        if request.args.get('party_id'):
            filters['party_id'] = int(request.args.get('party_id'))
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('register_number'):
            filters['register_number'] = int(request.args.get('register_number'))
        
        # Only pass filters if they exist
        kwargs = {}
        if page is not None and page_size is not None:
            kwargs['page'] = page
            kwargs['page_size'] = page_size
        if filters:
            kwargs['filters'] = filters
            
        result = retrieve_register_entry.get_all_register_entries_with_names(**kwargs)
        
        if result['status'] == 'error':
            return jsonify(result), 500
        return json.dumps(result, cls=CustomEncoder)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route(BASE + '/v2/get_all_memo_entries', methods=['GET'])
@jwt_required()
@permission_required('memo_entry', 'read')
def get_all_memo_entries_with_names():
    """Retrieves all memo entries with supplier and party names."""
    try:
        # Get pagination parameters
        page = request.args.get('page', type=int)
        page_size = request.args.get('page_size', type=int)
        
        # Get filter parameters
        filters = {}
        if request.args.get('supplier_id'):
            filters['supplier_id'] = int(request.args.get('supplier_id'))
        if request.args.get('party_id'):
            filters['party_id'] = int(request.args.get('party_id'))
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        if request.args.get('memo_number'):
            filters['memo_number'] = int(request.args.get('memo_number'))
        
        # Only pass filters if they exist
        kwargs = {}
        if page is not None and page_size is not None:
            kwargs['page'] = page
            kwargs['page_size'] = page_size
        if filters:
            kwargs['filters'] = filters
            
        result = retrieve_memo_entry.get_all_memo_entries_with_names(**kwargs)
        
        if result['status'] == 'error':
            return jsonify(result), 500
        return json.dumps(result, cls=CustomEncoder)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # Important: Disable reloader when using APScheduler in debug mode
    # otherwise the scheduler might run twice.
    # Set use_reloader=False when running with 'flask run'
    # or pass it to app.run directly if using that.
    app.run(debug=True, use_reloader=False)

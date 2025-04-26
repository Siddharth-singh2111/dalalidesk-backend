from __future__ import annotations
from typing import Union, List, Optional
from datetime import datetime, timedelta
import datetime
from typing import Dict
from Exceptions import DataError
from psql import db_connector, execute_query
from API_Database.utils import parse_date, sql_date
from API_Database.retrieve_partial_payment import get_partial_payment
from API_Database.retrieve_partial_payment import get_partial_payment_bulk
from pypika import Query, Table, Field, functions as fn, Order, Case
import sys
import math
sys.path.append('../')

def check_new_memo(memo_number: int, date: datetime, *args, **kwargs) -> bool:
    """
    Check if the memo already exists.
    """
    query = "select register_date, supplier_id, party_id from memo_entry where memo_number = '{}' order by 1 DESC".format(memo_number)
    response = execute_query(query)
    result = response['result']
    if len(result) == 0:
        return True
    return False

def check_add_memo(memo_number: int, memo_date: str) -> bool:
    """
    Check if the memo already exists.
    """
    (db, cursor) = db_connector.cursor()
    query = "select register_date from memo_entry where memo_number = '{}' order by 1 DESC".format(memo_number)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    if len(data) == 0:
        return True
    return False


def get_next_available_memo_number() -> int:
    """
    Get the next available memo number
    """
    query = 'select memo_number from memo_entry order by memo_number DESC;'
    response = execute_query(query)
    if len(response['result']) == 0:
        raise DataError('No Memo Entries Found, please contact Vaibhav')
    return response['result'][0]['memo_number'] + 1

def get_memo_entry_id(supplier_id: int, party_id: int, memo_number: int) -> int:
    """
    Get the memo_id using memo_number, supplier_id and party_id
    """
    query = 'select id from memo_entry where memo_number = {} AND supplier_id = {} AND party_id = {} order by register_date DESC;'.format(memo_number, supplier_id, party_id)
    response = execute_query(query)
    if len(response['result']) == 0:
        raise DataError(f'No memo entry found with memo_number: {memo_number}, supplier_id: {supplier_id}, party_id: {party_id}')
    elif len(response['result']) > 1:
        raise DataError(f'Multiple memo entries found with memo_number: {memo_number}, supplier_id: {supplier_id}, party_id: {party_id}')
    return int(response['result'][0]['id'])

def get_memo_bill_id(memo_id: int, bill_id: Optional[int], type: str, amount: int) -> int:
    """Constructs and executes a query to retrieve a memo bill ID based on memo details; raises DataError if no result is found."""
    memo_bills = Table('memo_bills')
    query = Query.from_(memo_bills).select(memo_bills.id).where((memo_bills.memo_id == memo_id) & (memo_bills.type == type) & (memo_bills.amount == amount))
    if bill_id is not None:
        query = query.where(memo_bills.bill_id == bill_id)
    sql = query.get_sql()
    response = execute_query(sql)
    if len(response['result']) == 0:
        raise DataError(f'No memo bill found with memo_id: {memo_id}, bill_id: {bill_id}, type: {type}, amount: {amount}')
    return response['result'][0]['id']

def get_memo_bills_by_id(memo_id: int) -> Dict:
    """Retrieves memo bills for a given memo ID and returns the results as a dictionary."""
    memo_bills = Table('memo_bills')
    query = Query.from_(memo_bills).select(memo_bills.id, memo_bills.bill_id, memo_bills.type, memo_bills.amount).where(memo_bills.memo_id == memo_id).orderby(memo_bills.bill_id)
    sql = query.get_sql()
    response = execute_query(sql)
    return response['result']

def get_memo_entry(memo_id: int) -> Dict:
    """Retrieves a memo entry along with its associated payments and bills for a given memo ID."""
    memo_entry_table = Table('memo_entry')
    memo_payments_table = Table('memo_payments')
    memo_bills_table = Table('memo_bills')
    bank_table = Table('bank')
    register_entry_table = Table('register_entry')
    part_payments_table = Table('part_payments')
    supplier_table = Table('supplier')
    party_table = Table('party')
    users_table = Table('users')
    users_updated_table = Table('users').as_('users_updated')
    
    # Get memo entry data with supplier and party names
    select_query = Query.from_(memo_entry_table)\
        .left_join(supplier_table).on(memo_entry_table.supplier_id == supplier_table.id)\
        .left_join(party_table).on(memo_entry_table.party_id == party_table.id)\
        .left_join(users_table).on(memo_entry_table.created_by == users_table.id)\
        .left_join(users_updated_table).on(memo_entry_table.last_updated_by == users_updated_table.id)\
        .select(
            memo_entry_table.star,
            supplier_table.name.as_('supplier_name'),
            party_table.name.as_('party_name'),
            users_table.full_name.as_('created_by_name'),
            users_updated_table.full_name.as_('updated_by_name')
        )\
        .where(memo_entry_table.id == memo_id)
    
    memo_data = execute_query(select_query.get_sql())['result'][0]
    
    # Get payment data
    select_query = Query.from_(memo_payments_table)\
        .join(bank_table).on(memo_payments_table.bank_id == bank_table.id)\
        .select(
            memo_payments_table.bank_id,
            bank_table.name.as_('bank_name'),
            memo_payments_table.cheque_number,
            memo_payments_table.amount
        )\
        .where(memo_payments_table.memo_id == memo_id)
    
    payments_data = execute_query(select_query.get_sql())['result']
    payments = [
        {
            'bank_id': p['bank_id'],
            'bank_name': p['bank_name'],
            'cheque_number': p['cheque_number'],
            'amount': p.get('amount', 0)
        }
        for p in payments_data
    ]
    
    # Get memo bills data
    select_query = Query.from_(memo_bills_table)\
        .left_join(register_entry_table).on(memo_bills_table.bill_id == register_entry_table.id)\
        .select(
            memo_bills_table.id,
            memo_bills_table.bill_id,
            register_entry_table.bill_number,
            memo_bills_table.type,
            memo_bills_table.amount
        )\
        .where(memo_bills_table.memo_id == memo_id)\
        .orderby(register_entry_table.bill_number)
    
    bills_data = execute_query(select_query.get_sql())['result']
    for bill in bills_data:
        if bill['bill_number'] is None:
            if bill['type'] == 'ST':
                bill['bill_number'] = -2
            elif bill['type'] == 'PR':
                bill['bill_number'] = -1
    
    
    # Determine mode
    mode = 'Full'
    for bill in bills_data:
        if bill['type'] == 'PR':
            mode = 'Part'
            break
        elif bill['type'] == 'ST':
            mode = 'Settlement'
            break
    
    # Get part payments if full mode
    part_payments = []
    if mode == 'Full':
        # Join with memo_entry to get memo_number and amount
        select_query = Query.from_(part_payments_table)\
            .join(memo_entry_table.as_('me')).on(part_payments_table.memo_id == memo_entry_table.as_('me').id)\
            .select(
                part_payments_table.id,
                part_payments_table.memo_id,
                memo_entry_table.as_('me').memo_number,
                memo_entry_table.as_('me').amount
            )\
            .where(part_payments_table.use_memo_id == memo_id)
        
        part_payments_data = execute_query(select_query.get_sql())['result']
        
        # Create a list of dictionaries with memo_id, memo_number, and amount
        part_details = [
            {
                'memo_id': p['memo_id'],
                'memo_number': p['memo_number'],
                'amount': p['amount']
            } for p in part_payments_data
        ]
        part_payments = [p['memo_id'] for p in part_details]
    
    # Parse JSON fields
    import json
    
    def parse_json_field(field_value, default=None):
        if not field_value:
            return default or []
            
        # Handle case where field_value is already parsed (not a string)
        if not isinstance(field_value, str):
            return field_value
            
        try:
            parsed_value = json.loads(field_value)
            return parsed_value
        except json.JSONDecodeError as e:
            # Log the error and the problematic value
            print(f"Error parsing JSON field: {e}")
            print(f"Field value: {repr(field_value)}")
            
            # If it's a string but not valid JSON, and looks like a list, 
            # try to handle it with special treatment for newlines
            if field_value.startswith('[') and field_value.endswith(']'):
                try:
                    # Try one more time with escaped newlines
                    return json.loads(field_value.replace('\n', '\\n'))
                except:
                    # If still failing, just return the string as a single item in a list
                    return [field_value[1:-1].strip('"')]
            
            return default or []
    
    # Construct result
    result = {
        'id': memo_data['id'],
        'memo_number': memo_data['memo_number'],
        'supplier_id': memo_data['supplier_id'],
        'party_id': memo_data['party_id'],
        'supplier_name': memo_data['supplier_name'],
        'party_name': memo_data['party_name'],
        'amount': memo_data['amount'],
        'gr_amount': memo_data.get('gr_amount', 0),
        'deduction': memo_data.get('deduction', 0),
        'register_date': sql_date(memo_data['register_date']),
        'mode': mode,
        'memo_bills': bills_data,
        'payment': payments,
        # New fields
        'discount': memo_data.get('discount', 0),
        'other_deduction': memo_data.get('other_deduction', 0),
        'rate_difference': memo_data.get('rate_difference', 0),
        'less_details': {
            'gr_amount': parse_json_field(memo_data.get('gr_amount_details')),
            'discount': parse_json_field(memo_data.get('discount_details')),
            'other_deduction': parse_json_field(memo_data.get('other_deduction_details')),
            'rate_difference': parse_json_field(memo_data.get('rate_difference_details'))
        },
        'notes': parse_json_field(memo_data.get('notes')),
        'parent_dalali_id': memo_data.get('parent_dalali_id'),
        'parent_memo_id': memo_data.get('parent_memo_id'),
        'memo_type': memo_data.get('memo_type', mode),  # Default to mode if memo_type not set
        'less_gst': memo_data.get('less_gst', 0),
        'commision': memo_data.get('commision', 0),
        'created_by': memo_data.get('created_by'),
        'created_by_name': memo_data.get('created_by_name', ''),
        'last_updated_by': memo_data.get('last_updated_by'),
        'updated_by_name': memo_data.get('updated_by_name', '')
    }
    
    if part_payments:
        result['selected_part'] = part_payments
        result['part_details'] = part_details
    
    return result

def get_all_memo_entries(**kwargs):
    """
    Get all memo entries only from memo_entry table
    Designed to use for the view menu filtering
    """
    memo_entry_table = Table('memo_entry')
    select_query = Query.from_(memo_entry_table).select(memo_entry_table.id)
    if 'supplier_id' in kwargs:
        supplier_id = int(kwargs['supplier_id'])
        select_query = select_query.where(memo_entry_table.supplier_id == supplier_id)
    if 'party_id' in kwargs:
        party_id = int(kwargs['party_id'])
        select_query = select_query.where(memo_entry_table.party_id == party_id)
    sql = select_query.get_sql()
    response = execute_query(sql)
    memo_entries = response['result']
    memo_entries_json: List[Dict] = []
    for memo_entry in memo_entries:
        memo_id = memo_entry['id']
        memo_entries_json.append(get_memo_entry(memo_id))
    return memo_entries_json

def get_total_memo_entity_bulk(supplier_ids: List[int], party_ids: List[int], start_date: datetime.datetime, end_date: datetime.datetime, memo_type: str, supplier_all: bool=False, party_all: bool=False):
    """
    Get total memo amount for multiple suppliers and parties in one query.
    Optimized version that fetches data in bulk when all suppliers/parties are selected.
    """
    if memo_type == 'PR':
        result = get_partial_payment_bulk(supplier_ids, party_ids, supplier_all, party_all)
        return sum((row['memo_amt'] for row in result))
    where_clauses = []
    if not supplier_all and supplier_ids:
        supplier_ids_str = ','.join(map(str, supplier_ids))
        where_clauses.append(f'memo_entry.supplier_id IN ({supplier_ids_str})')
    if not party_all and party_ids:
        party_ids_str = ','.join(map(str, party_ids))
        where_clauses.append(f'memo_entry.party_id IN ({party_ids_str})')
    where_clauses.extend([f"memo_bills.type = '{memo_type}'", f"memo_entry.register_date >= '{start_date}'", f"memo_entry.register_date <= '{end_date}'"])
    where_clause = ' AND '.join(where_clauses)
    query = '\n        SELECT COALESCE(SUM(memo_bills.amount), 0) as total_amount\n        FROM memo_bills\n        JOIN memo_entry ON memo_bills.memo_id = memo_entry.id\n        WHERE {}\n    '.format(where_clause)
    result = execute_query(query)
    return int(result['result'][0]['total_amount'])

def generate_memo_total(supplier_ids: Union[int, List[int]], party_ids: Union[int, List[int]], start_date: datetime, end_date: datetime, memo_type: str, supplier_all: bool=False, party_all: bool=False):
    """
    Generates the total for the given supplier_ids and party_ids for memo_bills.
    Uses bulk query for better performance.
    """
    if isinstance(supplier_ids, int):
        supplier_ids = [supplier_ids]
    if isinstance(party_ids, int):
        party_ids = [party_ids]
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    if isinstance(end_date, str):
        end_date = parse_date(end_date)
    return get_total_memo_entity_bulk(supplier_ids, party_ids, start_date, end_date, memo_type, supplier_all=supplier_all, party_all=party_all)

def get_all_memo_entries_with_names(page=None, page_size=None, filters=None) -> Dict:
    """Retrieves all memo entries with supplier and party names.
    
    Args:
        page: Optional page number for pagination (1-indexed)
        page_size: Optional number of items per page
        filters: Optional dictionary of filters to apply
    
    Returns:
        Dictionary with status and result
    """
    try:
        # Create table references
        memo_entry_table = Table('memo_entry')
        supplier_table = Table('supplier')
        party_table = Table('party')
        users_table = Table('users')
        users_updated_table = Table('users').as_('users_updated')
        mb = Table('memo_bills').as_('mb') # Alias for memo_bills

        # Columns from memo_entry table to select and group by
        memo_entry_cols_select = [
            memo_entry_table.id, memo_entry_table.memo_number, memo_entry_table.supplier_id,
            memo_entry_table.party_id, fn.ToChar(memo_entry_table.register_date, 'YYYY-MM-DD').as_('register_date'), 
            memo_entry_table.amount, memo_entry_table.gr_amount, memo_entry_table.deduction, 
            memo_entry_table.discount, memo_entry_table.other_deduction, memo_entry_table.rate_difference,
            memo_entry_table.gr_amount_details, memo_entry_table.discount_details,
            memo_entry_table.other_deduction_details, memo_entry_table.rate_difference_details,
            memo_entry_table.notes, memo_entry_table.last_update, memo_entry_table.created_at,
            memo_entry_table.created_by, memo_entry_table.last_updated, memo_entry_table.last_updated_by,
            memo_entry_table.parent_dalali_id, memo_entry_table.parent_memo_id, 
            memo_entry_table.memo_type, memo_entry_table.less_gst, memo_entry_table.commision
        ]
        # Columns needed for group by (without aliases/functions)
        memo_entry_cols_group = [
            memo_entry_table.id, memo_entry_table.memo_number, memo_entry_table.supplier_id,
            memo_entry_table.party_id, memo_entry_table.register_date, memo_entry_table.amount,
            memo_entry_table.gr_amount, memo_entry_table.deduction, memo_entry_table.discount,
            memo_entry_table.other_deduction, memo_entry_table.rate_difference,
            memo_entry_table.gr_amount_details, memo_entry_table.discount_details,
            memo_entry_table.other_deduction_details, memo_entry_table.rate_difference_details,
            memo_entry_table.notes, memo_entry_table.last_update, memo_entry_table.created_at,
            memo_entry_table.created_by, memo_entry_table.last_updated, memo_entry_table.last_updated_by,
            memo_entry_table.parent_dalali_id, memo_entry_table.parent_memo_id, 
            memo_entry_table.memo_type, memo_entry_table.less_gst, memo_entry_table.commision
        ]

        # Selected name columns + Aliases
        supplier_name_col = supplier_table.name.as_('supplier_name')
        party_name_col = party_table.name.as_('party_name')
        created_by_name_col = users_table.full_name.as_('created_by_name')
        updated_by_name_col = users_updated_table.full_name.as_('updated_by_name')
        name_cols_select = [supplier_name_col, party_name_col, created_by_name_col, updated_by_name_col]
        # Columns needed for group by (without aliases)
        name_cols_group = [supplier_table.name, party_table.name, users_table.full_name, users_updated_table.full_name]

        print("I am here")
        # Calculate memo_mode based on memo_bills types (ST > PR > Full)
        # Assign priority: 2 for 'ST', 1 for 'PR', 0 otherwise. Take the max priority.
        max_priority_subquery = fn.Coalesce(fn.Max(
            Case()
            .when(mb.type == 'ST', 2)
            .when(mb.type == 'PR', 1)
            .else_(0)
        ), 0)
        
        # Determine memo_mode based on the highest priority bill type found
        memo_mode_col = Case() \
            .when(max_priority_subquery == 2, 'Settlement') \
            .when(max_priority_subquery == 1, 'Part') \
            .else_('Full') \
            .as_('memo_mode')

        # All selected columns
        select_cols = memo_entry_cols_select + name_cols_select + [memo_mode_col]
        # Columns for GROUP BY
        group_by_cols = memo_entry_cols_group + name_cols_group

        # Build query with JOINs including the memo_bills table
        query = Query.from_(memo_entry_table)\
            .left_join(supplier_table).on(memo_entry_table.supplier_id == supplier_table.id)\
            .left_join(party_table).on(memo_entry_table.party_id == party_table.id)\
            .left_join(users_table).on(memo_entry_table.created_by == users_table.id)\
            .left_join(users_updated_table).on(memo_entry_table.last_updated_by == users_updated_table.id)\
            .left_join(mb).on(memo_entry_table.id == mb.memo_id)\
            .select(*select_cols)\
            .groupby(*group_by_cols)
        
        # Apply filters if provided
        if filters:
            if 'supplier_id' in filters and filters['supplier_id']:
                query = query.where(memo_entry_table.supplier_id == filters['supplier_id'])
            if 'party_id' in filters and filters['party_id']:
                query = query.where(memo_entry_table.party_id == filters['party_id'])
            if 'start_date' in filters and filters['start_date']:
                query = query.where(memo_entry_table.register_date >= filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                query = query.where(memo_entry_table.register_date <= filters['end_date'])
            if 'memo_number' in filters and filters['memo_number']:
                query = query.where(memo_entry_table.memo_number == filters['memo_number'])
        
        # Get total count for pagination (remains simple, based on memo_entry only before join/grouping)
        count_query = Query.from_(memo_entry_table).select(fn.Count('*').as_('total'))
        
        # Apply the same filters to count query
        if filters:
            if 'supplier_id' in filters and filters['supplier_id']:
                count_query = count_query.where(memo_entry_table.supplier_id == filters['supplier_id'])
            if 'party_id' in filters and filters['party_id']:
                count_query = count_query.where(memo_entry_table.party_id == filters['party_id'])
            if 'start_date' in filters and filters['start_date']:
                count_query = count_query.where(memo_entry_table.register_date >= filters['start_date'])
            if 'end_date' in filters and filters['end_date']:
                count_query = count_query.where(memo_entry_table.register_date <= filters['end_date'])
            if 'memo_number' in filters and filters['memo_number']:
                count_query = count_query.where(memo_entry_table.memo_number == filters['memo_number'])
        
        count_result = execute_query(count_query.get_sql())
        total_count = count_result['result'][0]['total'] if count_result['status'] == 'okay' else 0
        
        # Add order by to ensure consistent results (applied after grouping)
        # Ordering by created_at from memo_entry table
        query = query.orderby(memo_entry_table.created_at, order=Order.desc)

        # Apply pagination if requested (applied after grouping and ordering)
        if page is not None and page_size is not None:
            offset = (page - 1) * page_size
            query = query.limit(page_size).offset(offset)
            
        sql = query.get_sql()
        result = execute_query(sql)
        
        if result['status'] == 'error':
            return {'status': 'error', 'message': 'Failed to fetch memo entries'}
            
        memo_entries = result['result']
        

        return {
            'status': 'okay', 
            'result': memo_entries,
            'pagination': {
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': math.ceil(total_count / page_size) if page_size else 1
            } if page is not None and page_size is not None else None
        }
    except Exception as e:
        # Log the exception for debugging
        print(f"Error in get_all_memo_entries_with_names: {e}") 
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'message': str(e)}

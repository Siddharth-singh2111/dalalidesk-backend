from pypika import Query, Table, Criterion
from psql import execute_query

def search_entities(table_name: str, search_query: str, **kwargs):
    """
    Search for entities in the specified table that match the search query using PyPika.
    
    Args:
        table_name: The name of the table to search in
        search_query: The search query string
        **kwargs: Additional filters to apply. Special parameters:
            - field_filters: List of field filters with entityType, field, operator, and value
        
    Returns:
        List of entities that match the search criteria
    """
    # Define searchable fields based on entity type
    # Only including the five core entities: Supplier, Party, Bank, Register Entry, and Memo Entry
    searchable_fields = {
        'supplier': ['name', 'address', 'phone_number', 'city'],
        'party': ['name', 'address', 'phone_number'],
        'bank': ['name', 'address', 'phone_number'],
        # Expanded fields for Register Entry
        'register_entry': ['bill_number', 'amount', 'status', 'supplier_name', 'party_name'],
        # Expanded fields for Memo Entry
        'memo_entry': ['memo_number', 'amount', 'supplier_name', 'party_name'],
        'firm': ['name', 'address', 'phone_number'],
        'firm_bank': ['name', 'address', 'phone_number'],
    }
    
    fields = searchable_fields.get(table_name, ['name'])
    
    # Create table reference
    entity_table = Table(table_name)
    
    # For register_entry and memo_entry, we need to join with supplier and party
    if table_name in ['register_entry', 'memo_entry']:
        supplier_table = Table('supplier')
        party_table = Table('party')
        
        query = Query.from_(entity_table)\
            .left_join(supplier_table).on(entity_table.supplier_id == supplier_table.id)\
            .left_join(party_table).on(entity_table.party_id == party_table.id)\
            .select(
                entity_table.star,
                supplier_table.name.as_('supplier_name'),
                party_table.name.as_('party_name')
            )
    else:
        # Start building the query for other entities
        query = Query.from_(entity_table).select('*')
    
    # Build search criteria
    search_criteria = None
    for field in fields:
        # Handle numeric fields differently
        if field in ['bill_number', 'memo_number', 'order_form_number', 'quantity', 'rate', 'amount']:
            # Only apply numeric search if the search query is a number
            if search_query.isdigit():
                criterion = entity_table[field] == int(search_query)
                
                if search_criteria is None:
                    search_criteria = criterion
                else:
                    search_criteria = search_criteria | criterion
        # Handle supplier_id and party_id fields specially
        elif field in ['supplier_id', 'party_id'] and table_name in ['register_entry', 'memo_entry']:
            if search_query.isdigit():
                # If it's a number, search by ID
                criterion = entity_table[field] == int(search_query)
            else:
                # If it's text, don't search by ID (will be handled by supplier_name/party_name)
                continue
                
            if search_criteria is None:
                search_criteria = criterion
            else:
                search_criteria = search_criteria | criterion
        # Handle supplier_name and party_name fields
        elif field in ['supplier_name', 'party_name'] and table_name in ['register_entry', 'memo_entry']:
            if field == 'supplier_name':
                criterion = supplier_table.name.ilike(f'%{search_query}%')
            else:  # party_name
                criterion = party_table.name.ilike(f'%{search_query}%')
                
            if search_criteria is None:
                search_criteria = criterion
            else:
                search_criteria = search_criteria | criterion
        # Handle 'mode' field specially as it's a reserved keyword in PostgreSQL
        elif field == 'mode' and table_name == 'memo_entry':
            # Use the Field class to properly quote the field name
            from pypika import Field
            criterion = Field('mode').ilike(f'%{search_query}%')
            if search_criteria is None:
                search_criteria = criterion
            else:
                search_criteria = search_criteria | criterion
        else:
            # For text fields, use ILIKE for case-insensitive search
            criterion = entity_table[field].ilike(f'%{search_query}%')
            if search_criteria is None:
                search_criteria = criterion
            else:
                search_criteria = search_criteria | criterion
    
    # Add search criteria to query
    if search_criteria:
        query = query.where(search_criteria)
    
    # Extract special parameters
    field_filters = kwargs.pop('field_filters', None)
    
    # Process field filters if present
    if field_filters:
        try:
            # Only process filters for the current entity type
            entity_filters = [f for f in field_filters if f.get('entityType') == table_name]
            
            for filter_item in entity_filters:
                field = filter_item.get('field')
                operator = filter_item.get('operator')
                value = filter_item.get('value')
                
                if field and operator and value is not None:
                    # Handle supplier_name and party_name fields specially for joined tables
                    if field == 'supplier_name' and table_name in ['register_entry', 'memo_entry']:
                        field_ref = supplier_table.name
                    elif field == 'party_name' and table_name in ['register_entry', 'memo_entry']:
                        field_ref = party_table.name
                    # Handle 'mode' field specially as it's a reserved keyword in PostgreSQL
                    elif field == 'mode' and table_name == 'memo_entry':
                        from pypika import Field
                        field_ref = Field('mode')
                    else:
                        field_ref = entity_table[field]
                    
                    # Apply the appropriate operator
                    if operator == 'equals':
                        query = query.where(field_ref == value)
                    elif operator == 'notEquals':
                        query = query.where(field_ref != value)
                    elif operator == 'contains':
                        query = query.where(field_ref.ilike(f'%{value}%'))
                    elif operator == 'notContains':
                        query = query.where(field_ref.not_ilike(f'%{value}%'))
                    elif operator == 'startsWith':
                        query = query.where(field_ref.ilike(f'{value}%'))
                    elif operator == 'endsWith':
                        query = query.where(field_ref.ilike(f'%{value}'))
                    elif operator == 'greaterThan':
                        query = query.where(field_ref > value)
                    elif operator == 'lessThan':
                        query = query.where(field_ref < value)
                    elif operator == 'greaterThanOrEqual':
                        query = query.where(field_ref >= value)
                    elif operator == 'lessThanOrEqual':
                        query = query.where(field_ref <= value)
                    # Date operators would need date conversion logic
        except Exception as e:
            print(f"Error processing field filters: {str(e)}")
            # Continue with the query even if field filters fail
    
    # Add any additional filters from kwargs
    for key, value in kwargs.items():
        if key not in ['table_name', 'search', 'field_filters'] and value is not None:
            # Handle supplier_name and party_name fields specially for joined tables
            if key == 'supplier_name' and table_name in ['register_entry', 'memo_entry']:
                query = query.where(supplier_table.name == value)
            elif key == 'party_name' and table_name in ['register_entry', 'memo_entry']:
                query = query.where(party_table.name == value)
            # Handle 'mode' field specially as it's a reserved keyword in PostgreSQL
            elif key == 'mode' and table_name == 'memo_entry':
                from pypika import Field
                query = query.where(Field('mode') == value)
            else:
                query = query.where(entity_table[key] == value)
    
    # Get the SQL
    sql = query.get_sql()
    
    # Execute the query
    result = execute_query(sql)
    return result['result']

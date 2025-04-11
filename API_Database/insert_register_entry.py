from __future__ import annotations
from psql import execute_query
from API_Database import sql_date
from pypika import Query, Table
from Exceptions.custom_exception import DataError

def check_new_register(entry, edit_mode=False) -> bool:
    """
    Check if the register_entry is valid to insert or update.
    Rules:
    1. No exact duplicate (same bill number, supplier, party, and date) excluding self if edit_mode=True
    2. If bill number exists for same supplier and party, dates must be at least 6 months apart, excluding self if edit_mode=True
    """
    
    # Base WHERE clause components
    where_clause = f"""
        WHERE bill_number = '{entry.bill_number}' 
        AND supplier_id = '{entry.supplier_id}' 
        AND party_id = '{entry.party_id}'
    """
    
    # Add condition to exclude current entry's ID if in edit mode
    edit_mode_condition = ""
    if edit_mode:
        if not hasattr(entry, 'id') or entry.id is None:
            raise ValueError("Entry must have an 'id' attribute in edit mode.")
        edit_mode_condition = f" AND id != {entry.id}"

    # First check for exact duplicate
    exact_duplicate_query = f"""
        SELECT id, register_date 
        FROM register_entry 
        {where_clause}
        AND register_date = '{entry.register_date}'
        {edit_mode_condition}
    """
    
    response = execute_query(exact_duplicate_query)
    if len(response["result"]) > 0:
        # In edit mode, this means another record has the exact same details.
        # In insert mode, this means the record already exists.
        # We should raise an error here as the UI/caller should prevent exact duplicates.
        existing_id = response["result"][0]["id"]
        raise DataError({
            "status": "error",
            "message": "Exact duplicate entry found.",
            "input_errors": {
                "bill_number": {
                    "status": "error",
                    "message": f"An entry with Bill number {entry.bill_number}, Supplier ID {entry.supplier_id}, Party ID {entry.party_id}, and Date {entry.register_date} already exists (ID: {existing_id})."
                }
            }
        })


    # Then check for bills with same number but different dates
    similar_bills_query = f"""
        SELECT id, register_date 
        FROM register_entry 
        {where_clause}
        AND register_date != '{entry.register_date}'
        {edit_mode_condition}
        ORDER BY register_date
    """
    
    response = execute_query(similar_bills_query)
    existing_entries = response["result"]
    
    if existing_entries:
        new_date = entry.register_date
        for existing_entry in existing_entries:
            existing_date = existing_entry["register_date"]
            # Calculate months between dates using PostgreSQL
            months_diff_query = """
                SELECT ABS(
                    EXTRACT(year FROM AGE('{0}', '{1}')) * 12 +
                    EXTRACT(month FROM AGE('{0}', '{1}'))
                ) as months_between
            """.format(new_date, existing_date)
            
            response = execute_query(months_diff_query)
            months_between = response["result"][0]["months_between"]
            
            if months_between < 6:
                existing_id = existing_entry["id"]
                raise DataError({
                    "status": "error",
                    "message": "Duplicate Bill Number too close in time",
                    "input_errors": {
                        "bill_number": {
                            "status": "error",
                            "message": f"Bill number {entry.bill_number} already exists (ID: {existing_id}) with date {existing_date}. Duplicate bill numbers for the same supplier and party must be at least 6 months apart."
                        }
                    }
                })
    
    # If we reach here, the entry is valid
    return True

def insert_register_entry(entry) -> None:
    """
    Insert a register_entry into the database.
    """
    
    # Define the table
    register_entry_table = Table('register_entry')

    # Build the INSERT query using Pypika
    insert_query = Query.into(register_entry_table).columns(
        'supplier_id',
        'party_id',
        'register_date',
        'amount',
        'bill_number',
        'status',
        'gr_amount',
        'deduction'
    ).insert(
        entry.supplier_id,
        entry.party_id,
        entry.register_date,
        entry.amount,
        entry.bill_number,
        entry.status,
        entry.gr_amount,
        entry.deduction
    )

    # Get the raw SQL query and parameters from the Pypika query
    sql = insert_query.get_sql()

    # Execute the query
    return execute_query(sql)

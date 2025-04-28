from __future__ import annotations
from typing import List, Tuple
from psql import db_connector, execute_query
from pypika import Query, Table, Field, functions as fn
from Exceptions import DataError

def get_all_names_ids(name: str, dict_cursor: bool=True) -> dict:
    """
    Get all <name> ids and names returned in a dictionary
    """
    (db, cursor) = db_connector.cursor(dict_cursor)
    query = f'select id, name from {name} order by name;'
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data

def get_party_name_by_id(party_id: int) -> str:
    """
    Get party name by ID
    """
    (db, cursor) = db_connector.cursor()
    query = "select name from party where id = '{}';".format(party_id)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data[0][0]

def get_supplier_name_by_id(supplier_id: int) -> str:
    """
    Get supplier name by ID
    """
    (db, cursor) = db_connector.cursor()
    query = "select name from supplier where id = '{}';".format(supplier_id)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data[0][0]

def get_firm_name_by_id(firm_id: int) -> str:
    """
    Get firm name by ID
    """
    (db, cursor) = db_connector.cursor()
    query = "select name from firm where id = '{}';".format(firm_id)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data[0][0]

def get_firm_bank_name_by_id(firm_bank_id: int) -> str:
    """
    Get firm bank name by ID
    """
    (db, cursor) = db_connector.cursor()
    query = "select name from firm_bank where id = '{}';".format(firm_bank_id)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()
    return data[0][0]

def get_individual_id_by_name(name: str, table_name: str) -> int:
    """Retrieves the ID of an individual from the specified table based on the given name; raises DataError if not found."""
    entity_table = Table(table_name)
    query = Query.from_(entity_table).select('id').where(entity_table.name == name)
    sql = query.get_sql()
    data = execute_query(sql)
    result = data['result']
    if len(result) == 0:
        error_message = f'No {table_name} of name {name}'
        raise DataError(error_message)
    return result[0]['id']

def get_individual_by_id(id: int, table_name: str) -> dict:
    """
    Get individual data by ID
    """
    entity_table = Table(table_name)
    query = Query.from_(entity_table).select('*').where(entity_table.id == id)
    sql = query.get_sql()
    data = execute_query(sql)
    result = data['result']
    if len(result) == 0:
        error_message = f'No {table_name} of id {id}'
        raise DataError(error_message)
    if len(result) > 1:
        error_message = f'Multiple {table_name} of id {id}'
        raise DataError(error_message)
    return result[0]

def get_supplier_gst_default(supplier_id: int) -> float:
    """
    Get supplier's default GST percentage
    
    Args:
        supplier_id: The ID of the supplier
        
    Returns:
        The default GST percentage for the supplier (e.g., 5.0, 12.0)
        
    Raises:
        DataError: If the supplier is not found
    """
    try:
        supplier_data = get_individual_by_id(supplier_id, 'supplier')
        # Return the gst_default value, or 5.0 if not set
        return float(supplier_data.get('gst_default', 5.0))
    except Exception as e:
        # In case of any error, return the default value of 5.0
        return 5.0

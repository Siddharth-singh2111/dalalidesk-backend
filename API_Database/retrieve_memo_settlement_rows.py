from __future__ import annotations
from typing import Dict, List
from psql import db_connector, execute_query
from Exceptions import DataError

def get_memo_settlement_bulk(supplier_ids: List[int], party_ids: List[int], supplier_all: bool=False, party_all: bool=False) -> List[Dict]:
    """
    Returns the settlement memos for multiple suppliers and parties.
    Optimized version that fetches data in bulk when all suppliers/parties are selected.
    """
    where_clauses = []
    if not supplier_all and supplier_ids:
        supplier_ids_str = ','.join(map(str, supplier_ids))
        where_clauses.append(f'memo_entry.supplier_id IN ({supplier_ids_str})')
    if not party_all and party_ids:
        party_ids_str = ','.join(map(str, party_ids))
        where_clauses.append(f'memo_entry.party_id IN ({party_ids_str})')
    where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
    
    query = f"""
        SELECT
            memo_entry.supplier_id as supplier_id, 
            memo_entry.party_id as party_id,
            memo_entry.memo_number as memo_no,
            to_char(memo_entry.register_date, 'DD/MM/YYYY') as memo_date,
            memo_entry.amount as chk_amt,
            memo_bills.amount as memo_amt,
            memo_bills.type as memo_type
        FROM memo_entry
        JOIN memo_bills ON memo_entry.id = memo_bills.memo_id
        JOIN supplier ON memo_entry.supplier_id = supplier.id
        JOIN party ON memo_entry.party_id = party.id
        WHERE (memo_bills.type = 'ST' OR memo_bills.type = 'DT') AND {where_clause}
        ORDER BY supplier.name, party.name, memo_entry.register_date, memo_entry.memo_number;
    """
    
    result = execute_query(query)
    return result['result']

def get_memo_settlement(supplier_id: int, party_id: int) -> List[Dict]:
    """
    Returns the settlement memos between the party and supplier.
    Single supplier-party version that calls the bulk version for consistency.
    """
    return get_memo_settlement_bulk([supplier_id], [party_id])

def get_memo_settlement_by_id(memo_id: int) -> Dict:
    """Retrieves settlement memo details for a given memo ID;
    raises DataError if not exactly one record is found.
    """
    query = f"""
        SELECT 
            mb.id, 
            mb.memo_id, 
            mb.amount,
            mb.type,
            me.memo_number
        FROM 
            memo_bills mb
        JOIN 
            memo_entry me ON mb.memo_id = me.id
        WHERE 
            mb.memo_id = {memo_id} AND (mb.type = 'ST' OR mb.type = 'DT')
    """
    response = execute_query(query)
    num_results = len(response['result'])
    if num_results != 1:
        raise DataError(f'Expected exactly one settlement record for memo_id: {memo_id}, but found {num_results}')
    return response['result'][0]

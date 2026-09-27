from __future__ import annotations
import sys
sys.path.append("../")
from psql import db_connector


def get_credit(supplier_id: int, party_id: int) -> dict:
    """
    Returns the partial payment without bill between the party and supplier.
    """
    # Open a new connection
    db, cursor = db_connector.cursor(True)
    
    query = "select partial_amount from supplier_party_account where supplier_id = '{}' AND party_id = '{}'".format(supplier_id, party_id)
    cursor.execute(query)
    data = cursor.fetchall()
    db.close()

    return data

def get_pending_part(supplier_id: int, party_id: int) -> dict:
    """
    Returns the partial payments between the party and supplier.
    """
    # Open a new connection
    db, cursor = db_connector.cursor(True)
    
    # Find all the partial payments with given supplier_id and party_id that are not used
    query = "SELECT * FROM part_payments WHERE supplier_id = '{}' AND party_id = '{}' AND used = false".format(supplier_id, party_id)
    cursor.execute(query)
    data = cursor.fetchall()

    # Retrieve memo bills with type="PR" for each row
    for row in data:
        memo_id = row['memo_id']
        # Fetch memo bills associated with the memo_id
        memo_bills_query = "SELECT memo_entry.id as memo_id, memo_entry.memo_number as memo_number, memo_entry.is_out_station as is_out_station, memo_bills.id AS bill_id, memo_bills.amount, to_char(memo_entry.register_date, 'DD/MM/YYYY') as date FROM memo_entry INNER JOIN memo_bills ON memo_entry.id = memo_bills.memo_id WHERE memo_entry.id = '{}' AND memo_bills.type = 'PR'".format(memo_id)
        cursor.execute(memo_bills_query)
        memo_bills = cursor.fetchall()
        row['memo_bills'] = memo_bills
    db.close()
    
    r_data = []
    for row in data:
        for bill in row['memo_bills']:
            r_data.append(bill)
    return r_data

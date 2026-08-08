from __future__ import annotations
from psql import db_connector, execute_query
from API_Database import retrieve_memo_entry
import datetime
import json
from typing import Dict
from Entities import MemoEntry
import sys
sys.path.append('../')

def update_memo_entry_data(entry: MemoEntry) -> None:
    """
    Update changes made to  a memo_entry
    """
    (db, cursor) = db_connector.cursor()
    entry_id = MemoEntry.get_memo_entry_id(entry.supplier_id, entry.party_id, entry.memo_number)
    if entry.mode != 'Good Return':
        query = "UPDATE memo_entry SET amount = amount + '{}' WHERE id = {}".format(entry.amount, entry_id)
    else:
        query = "UPDATE memo_entry SET gr_amount = gr_amount + '{}' WHERE id = {}".format(entry.amount, entry_id)
    cursor.execute(query)
    db.commit()
    db.close()

def update_memo_amount(id: int, custom_amount: int=0):
    """Calculates and updates the memo entry amount based on its associated memo bills; returns nothing."""
    (db, cursor) = db_connector.cursor(True)
    query = f'SELECT supplier_id, party_id, memo_bills.amount as amount, memo_bills.type as type, memo_bills.bill_number as bill_number from memo_bills join memo_entry on memo_bills.memo_id = memo_entry.id where memo_bills.memo_id = {id}'
    cursor.execute(query)
    data = cursor.fetchall()
    amount = 0
    for bills in data:
        if bills['type'] in ['D', 'G', 'C']:
            pass
        else:
            amount += bills['amount']
    if custom_amount != 0:
        amount = custom_amount
    query = f'UPDATE memo_entry SET amount = {amount} WHERE id = {id}'
    cursor.execute(query)
    db.commit()
    db.close()

def update_memo_amount_and_commission(memo_id: int, amount: int, less_gst: int, commision: int, less_gst_percentage=None):
    """
    Update a memo's amount and recalculated commission fields (used when bills are
    added to an existing memo). Uses execute_query so the audit trail is recorded.
    """
    query = (
        f"UPDATE memo_entry SET amount = {int(amount)}, less_gst = {int(less_gst)}, "
        f"commision = {int(commision)}"
    )
    if less_gst_percentage is not None:
        query += f", less_gst_percentage = {float(less_gst_percentage)}"
    query += f" WHERE id = {int(memo_id)}"
    return execute_query(query)

def update_memo_entry_from_obj(data: Dict):
    """Updates a memo entry using a provided data dictionary and returns the update status."""
    (db, cursor) = db_connector.cursor(True)
    memo_number = int(data['memo_number'])
    supplier_id = int(data['supplier_id'])
    party_id = int(data['party_id'])
    register_date = datetime.datetime.strptime(data['register_date'], '%Y-%m-%d')
    memo_id = int(data['id'])

    query = f"UPDATE memo_entry SET memo_number = {memo_number}, supplier_id={supplier_id}, party_id = {party_id}, register_date='{register_date}' where id={memo_id}"
    
    # # Initialize new fields with default values
    # amount = int(data.get('amount', 0))
    # gr_amount = int(data.get('gr_amount', 0))
    # deduction = int(data.get('deduction', 0))
    # discount = int(data.get('discount', 0))
    # other_deduction = int(data.get('other_deduction', 0))
    # rate_difference = int(data.get('rate_difference', 0))
    
    # # Process less_details if present
    # gr_amount_details = json.dumps(data.get('less_details', {}).get('gr_amount', [])) if 'less_details' in data and 'gr_amount' in data['less_details'] else None
    # discount_details = json.dumps(data.get('less_details', {}).get('discount', [])) if 'less_details' in data and 'discount' in data['less_details'] else None
    # other_deduction_details = json.dumps(data.get('less_details', {}).get('other_deduction', [])) if 'less_details' in data and 'other_deduction' in data['less_details'] else None
    # rate_difference_details = json.dumps(data.get('less_details', {}).get('rate_difference', [])) if 'less_details' in data and 'rate_difference' in data['less_details'] else None
    
    # # Process notes if present
    # notes = json.dumps(data.get('notes', [])) if 'notes' in data else None
    
    # # Build the query with all fields
    # query = f"""
    # UPDATE memo_entry SET 
    #     memo_number = {memo_number}, 
    #     supplier_id = {supplier_id}, 
    #     party_id = {party_id}, 
    #     register_date = '{register_date}',
    #     amount = {amount},
    #     gr_amount = {gr_amount},
    #     deduction = {deduction},
    #     discount = {discount},
    #     other_deduction = {other_deduction},
    #     rate_difference = {rate_difference}
    # """
    
    # # Add JSON fields if they exist
    # if gr_amount_details:
    #     query += f", gr_amount_details = '{gr_amount_details}'"
    # if discount_details:
    #     query += f", discount_details = '{discount_details}'"
    # if other_deduction_details:
    #     query += f", other_deduction_details = '{other_deduction_details}'"
    # if rate_difference_details:
    #     query += f", rate_difference_details = '{rate_difference_details}'"
    # if notes:
    #     query += f", notes = '{notes}'"
    
    # # Complete the query
    # query += f" WHERE id = {memo_id}"
    
    try:
        cursor.execute(query)
    except Exception as e:
        return {'status': 'error', 'message': f'Could not update Memo Entry: {str(e)}. Please contact Vaibhav'}
    
    db.commit()
    db.close()
    return {'status': 'okay'}

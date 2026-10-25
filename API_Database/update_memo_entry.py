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


def rewrite_memo_entry_row(memo_id: int, entry) -> Dict:
    """
    Memo edit: overwrite the memo_entry row with the edited memo's values. The
    id, memo number, supplier, party and out-station series never change.
    Runs through execute_query, so it joins an open transaction() and is audited.
    """
    from pypika import Query, Table
    t = Table('memo_entry')

    def dump(value):
        return json.dumps(value) if value else None

    query = (
        Query.update(t)
        .set(t.register_date, entry.register_date)
        .set(t.amount, entry.amount)
        .set(t.gr_amount, entry.gr_amount)
        .set(t.deduction, entry.deduction)
        .set(t.discount, entry.discount)
        .set(t.other_deduction, entry.other_deduction)
        .set(t.rate_difference, entry.rate_difference)
        .set(t.additions, entry.additions)
        .set(t.gr_amount_details, dump(entry.gr_amount_details))
        .set(t.discount_details, dump(entry.discount_details))
        .set(t.other_deduction_details, dump(entry.other_deduction_details))
        .set(t.rate_difference_details, dump(entry.rate_difference_details))
        .set(t.additions_details, dump(entry.additions_details))
        .set(t.notes, dump(entry.notes))
        .set(t.parent_dalali_id, entry.parent_dalali_id)
        .set(t.parent_memo_id, entry.parent_memo_id)
        .set(t.memo_type, entry.memo_type)
        .set(t.less_gst_percentage, getattr(entry, 'less_gst_percentage', None))
        .set(t.less_gst, entry.less_gst)
        .set(t.commision, entry.commision)
        .where(t.id == int(memo_id))
    )
    return execute_query(query.get_sql())

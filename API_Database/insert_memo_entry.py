from __future__ import annotations
from typing import Dict
from psql import db_connector, execute_query
from API_Database import retrieve_memo_entry, sql_date
from Entities import MemoEntry, MemoBill
from .update_partial_amount import update_part_payment
from Exceptions import DataError
from pypika import Query, Table
import json

def insert_memo_entry(entry: MemoEntry) -> Dict:
    """Inserts a memo entry along with its bills and payments into the database; returns the insertion status."""
    status = insert_memo(entry)
    memo_id = MemoEntry.get_memo_entry_id(entry.supplier_id, entry.party_id, entry.memo_number)
    for bill in entry.memo_bills:
        status = insert_memo_bill(bill, memo_id)
    for payment in entry.payment:
        payment['memo_id'] = memo_id
        status = insert_memo_payment(payment)
    if entry.mode == 'Full':
        for part_memo_id in entry.part_payment:
            status = update_part_payment(entry.supplier_id, entry.party_id, memo_id=part_memo_id, use_memo_id=memo_id)
        return status
    elif entry.mode == 'Part':
        return insert_part_memo(entry, memo_id)
    elif entry.mode == 'Payment Settlement':
        return status
    elif entry.mode == 'Dalali Settlement':
        return status
    else:
        raise DataError('Invalid Memo Type')

def insert_memo(entry: MemoEntry) -> None:
    """
    Insert a memo_entry into the memo_entry table.
    """
    memo_entry_table = Table('memo_entry')
    
    # Serialize the detail lists to JSON strings
    gr_amount_details_json = json.dumps(entry.gr_amount_details) if entry.gr_amount_details else None
    discount_details_json = json.dumps(entry.discount_details) if entry.discount_details else None
    other_deduction_details_json = json.dumps(entry.other_deduction_details) if entry.other_deduction_details else None
    rate_difference_details_json = json.dumps(entry.rate_difference_details) if entry.rate_difference_details else None
    notes_json = json.dumps(entry.notes) if entry.notes else None
    
    insert_query = Query.into(memo_entry_table).columns(
        'supplier_id', 'party_id', 'memo_number', 'register_date', 'amount', 
        'gr_amount', 'deduction', 'discount', 'other_deduction', 'rate_difference',
        'gr_amount_details', 'discount_details', 'other_deduction_details', 
        'rate_difference_details', 'notes',
        'parent_dalali_id', 'parent_memo_id', 'memo_type', 
        'less_gst_percentage', 'less_gst', 'commision'
    ).insert(
        entry.supplier_id, entry.party_id, entry.memo_number, entry.register_date, 
        entry.amount, entry.gr_amount, entry.deduction, entry.discount, 
        entry.other_deduction, entry.rate_difference, gr_amount_details_json,
        discount_details_json, other_deduction_details_json, rate_difference_details_json,
        notes_json, entry.parent_dalali_id, entry.parent_memo_id, entry.memo_type,
        entry.less_gst_percentage, entry.less_gst, entry.commision
    )
    
    sql = insert_query.get_sql()
    result = execute_query(sql)
    
    # Update the less_gst_percentage separately if it exists
    if hasattr(entry, 'less_gst_percentage') and entry.less_gst_percentage is not None:
        memo_id = MemoEntry.get_memo_entry_id(entry.supplier_id, entry.party_id, entry.memo_number)
        memo_entry_table = Table('memo_entry')
        update_query = Query.update(memo_entry_table).set(
            memo_entry_table.less_gst_percentage, entry.less_gst_percentage
        ).where(memo_entry_table.id == memo_id)
        update_sql = update_query.get_sql()
        execute_query(update_sql)
        
    return result

def insert_memo_bill(entry: MemoBill, memo_id: int) -> None:
    """
    Insert all the bills attached to the same memo number.
    """
    memo_bills_table = Table('memo_bills')
    insert_query = Query.into(memo_bills_table).columns('memo_id', 'bill_id', 'type', 'amount').insert(memo_id, entry.bill_id, entry.type, entry.amount)
    sql = insert_query.get_sql()
    if entry.bill_id is None:
        sql = sql.replace(f'{entry.bill_id}', 'NULL')
    return execute_query(sql)

def insert_memo_payment(payment: Dict) -> None:
    """
    Add the memo payments for the given memo_entry
    """
    memo_payments_table = Table('memo_payments')
    
    # Default amount to 0 if not present
    amount = payment.get('amount', 0)
    
    insert_query = Query.into(memo_payments_table).columns(
        'memo_id', 'bank_id', 'cheque_number', 'amount'
    ).insert(
        payment['memo_id'], payment['bank_id'], payment['cheque_number'], amount
    )
    
    sql = insert_query.get_sql()
    return execute_query(sql)

def insert_part_memo(entry: MemoEntry, memo_id) -> None:
    """
    Insert all the bills attached to the same memo number.
    """
    part_payments_table = Table('part_payments')
    insert_query = Query.into(part_payments_table).columns('supplier_id', 'party_id', 'memo_id').insert(entry.supplier_id, entry.party_id, memo_id)
    sql = insert_query.get_sql()
    return execute_query(sql)

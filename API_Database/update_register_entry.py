from __future__ import annotations
from Entities import RegisterEntry
from API_Database import retrieve_register_entry
from psql import execute_query

def update_register_entry_data(entry: RegisterEntry) -> None:
    """
    Update changes made to the register entry by a memo_entry
    """
    entry_id = entry.get_id()
    return update_register_entry_by_id(entry, entry_id)

def _sql_text(value) -> str:
    """A nullable text value as a SQL literal (quotes escaped; empty -> NULL)."""
    if value is None or str(value).strip() == '':
        return 'NULL'
    return "'" + str(value).strip().replace("'", "''") + "'"

def update_register_entry_by_id(entry: RegisterEntry, entry_id: int):
    """Updates a register entry identified by its ID with new data; returns the execution status."""
    # L.R. No. and transport name are updated only when the entry carries them
    # (bill edit form, or a bill loaded from the database), never wiped by a
    # caller that didn't load them.
    dispatch = ''
    if getattr(entry, 'dispatch_fields_loaded', False):
        dispatch = ", lr_number = {}, transport_name = {}".format(_sql_text(entry.lr_number), _sql_text(entry.transport_name))
    query = "UPDATE register_entry SET supplier_id= {}, party_id= {}, register_date = '{}', amount = {}, partial_amount = '{}', status = '{}', deduction = '{}', gr_amount = '{}', bill_number = {}{} WHERE id = {}".format(entry.supplier_id, entry.party_id, str(entry.register_date), entry.amount, entry.partial_amount, entry.status, entry.deduction, entry.gr_amount, entry.bill_number, dispatch, entry_id)
    return execute_query(query)
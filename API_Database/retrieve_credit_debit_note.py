from __future__ import annotations
from typing import Dict
from psql import execute_query
from pypika import Query, Table, functions as fn, Order
from Exceptions import DataError


def get_all_credit_debit_notes(**kwargs):
    """
    List credit/debit notes with supplier and party names, newest first.
    Optional filters: supplier_id, party_id.
    """
    cdn = Table('credit_debit_note')
    supplier = Table('supplier')
    party = Table('party')

    select_query = Query.from_(cdn)\
        .left_join(supplier).on(cdn.supplier_id == supplier.id)\
        .left_join(party).on(cdn.party_id == party.id)\
        .select(
            cdn.id,
            cdn.note_type,
            cdn.note_number,
            fn.ToChar(cdn.note_date, 'YYYY-MM-DD').as_('note_date'),
            fn.Cast(cdn.amount, 'integer').as_('amount'),
            cdn.supplier_id,
            cdn.party_id,
            cdn.remark,
            supplier.name.as_('supplier_name'),
            party.name.as_('party_name')
        )

    if 'supplier_id' in kwargs and kwargs['supplier_id']:
        select_query = select_query.where(cdn.supplier_id == int(kwargs['supplier_id']))
    if 'party_id' in kwargs and kwargs['party_id']:
        select_query = select_query.where(cdn.party_id == int(kwargs['party_id']))

    select_query = select_query.orderby(cdn.note_date, order=Order.desc).orderby(cdn.id, order=Order.desc)
    response = execute_query(select_query.get_sql())
    return response['result']


def get_credit_debit_khata_rows_bulk(supplier_ids, party_ids, start_date, end_date,
                                     supplier_all: bool = False, party_all: bool = False):
    """
    Credit/debit notes shaped as Khata report rows (reusing the memo_* columns so
    they render inline with memos). memo_type is 'CN' (credit) or 'DN' (debit);
    the Khata totals use it to adjust the pending balance. Filtered by note_date
    within the range, and by supplier/party unless the *_all flags are set.
    """
    where = []
    if not supplier_all and supplier_ids:
        where.append(f"supplier_id IN ({','.join(str(int(s)) for s in supplier_ids)})")
    if not party_all and party_ids:
        where.append(f"party_id IN ({','.join(str(int(p)) for p in party_ids)})")
    where.append(f"note_date >= '{start_date}'")
    where.append(f"note_date <= '{end_date}'")
    where_clause = ' AND '.join(where)
    query = f"""
        SELECT supplier_id,
               party_id,
               (CASE WHEN note_type = 'Credit' THEN 'Credit Note' ELSE 'Debit Note' END
                || COALESCE(' #' || note_number, '')) AS memo_no,
               to_char(note_date, 'DD/MM/YYYY') AS memo_date,
               amount::integer AS memo_amt,
               '' AS chk_amt,
               CASE WHEN note_type = 'Credit' THEN 'CN' ELSE 'DN' END AS memo_type
        FROM credit_debit_note
        WHERE {where_clause}
        ORDER BY note_date, id
    """
    return execute_query(query)['result']


def get_credit_debit_note_by_id(id: int) -> Dict:
    """Retrieves a single credit/debit note (with supplier/party names) by its ID."""
    cdn = Table('credit_debit_note')
    supplier = Table('supplier')
    party = Table('party')

    select_query = Query.from_(cdn)\
        .left_join(supplier).on(cdn.supplier_id == supplier.id)\
        .left_join(party).on(cdn.party_id == party.id)\
        .select(
            cdn.id,
            cdn.note_type,
            cdn.note_number,
            fn.ToChar(cdn.note_date, 'YYYY-MM-DD').as_('note_date'),
            fn.Cast(cdn.amount, 'integer').as_('amount'),
            cdn.supplier_id,
            cdn.party_id,
            cdn.remark,
            supplier.name.as_('supplier_name'),
            party.name.as_('party_name')
        )\
        .where(cdn.id == id)

    data = execute_query(select_query.get_sql())
    if len(data['result']) == 0:
        raise DataError(f'No Credit/Debit Note with id: {id}')
    return data['result'][0]

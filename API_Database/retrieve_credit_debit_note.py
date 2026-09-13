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

from pypika import Query, Table
from psql import execute_query


def insert_credit_debit_note(entry) -> dict:
    """
    Insert a credit_debit_note row into the database.
    """
    credit_debit_note_table = Table('credit_debit_note')

    insert_query = Query.into(credit_debit_note_table).columns(
        'note_type',
        'note_number',
        'note_date',
        'amount',
        'supplier_id',
        'party_id',
        'remark',
        'created_by'
    ).insert(
        entry.note_type,
        entry.note_number,
        entry.note_date,
        entry.amount,
        entry.supplier_id,
        entry.party_id,
        getattr(entry, 'remark', None),
        getattr(entry, 'created_by', None)
    )

    sql = insert_query.get_sql()
    return execute_query(sql)

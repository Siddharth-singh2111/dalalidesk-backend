from psql import db_connector

def get_from_id(table_name: str, id: int):
    """Retrieves a record from a specified table by its ID, with custom queries for register_entry and memo_entry."""
    (db, cursor) = db_connector.cursor(True)
    sql = f'select * from {table_name} where id={id}'
    if table_name == 'register_entry':
        sql = f"select id, supplier_id, party_id, to_char(register_date, 'DD/MM/YYYY') as register_date,floor(amount)::integer as amount, floor(partial_amount)::integer as partial_amount, gr_amount, bill_number, status, deduction from register_entry"
    elif table_name == 'memo_entry':
        sql = f"select id, memo_number, is_out_station, supplier_id, party_id, to_char(register_date, 'DD/MM/YYYY') as register_date,floor(amount)::integer as amount, gr_amount from memo_entry"
    cursor.execute(sql)
    return cursor.fetchall()
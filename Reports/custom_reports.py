"""
Standalone JSON report generators (July 2026 batch):

- bills_added_report:          bills ENTERED (created_at) in a range, day-wise ->
                               supplier-wise, with who added them and totals.
- supplier_wise_sale:          sale (register entries) summarised per supplier.
- buyer_wise_sale:             sale summarised per party (buyer).
- supplier_wise_outstanding:   pending bills grouped per supplier with ageing.

They emit the same JSON shape as Reports/report.py (headings / subheadings /
dataRows / specialRows / cumulative) so the existing frontend table renderer and
the generic PDF exporter consume them unchanged.
"""
from typing import Dict, List, Optional
from datetime import datetime, date
from API_Database import parse_date, sql_date
from psql import execute_query


def _fmt(amount) -> str:
    """Indian-style currency grouping, integer rupees."""
    try:
        value = int(round(float(amount or 0)))
    except (TypeError, ValueError):
        value = 0
    negative = value < 0
    digits = str(abs(value))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ','.join(groups + [tail])
    return f"-{digits}" if negative else digits


def _total_row(name: str, numeric: int, column: str) -> Dict:
    return {'name': name, 'value': _fmt(numeric), 'column': column,
            'numeric': int(numeric), 'beforeData': False}


def _fmt_date(value) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime('%d/%m/%Y')
    return str(value or '')


def _id_filter(column: str, ids: List[int], select_all: bool) -> str:
    if select_all or not ids:
        return ''
    ids_str = ','.join(str(int(i)) for i in ids)
    return f' AND {column} IN ({ids_str})'


def _base(title: str, start_date: str, end_date: str) -> Dict:
    return {'title': title, 'from': start_date, 'to': end_date, 'headings': []}


def bills_added_report(supplier_ids: List[int], party_ids: List[int],
                       start_date: str, end_date: str,
                       supplier_all: bool = False, party_all: bool = False) -> Dict:
    """
    Bills grouped by the calendar day they were ENTERED into the software
    (register_entry.created_at), then by supplier. Columns per item spec:
    party, bill number, bill date, amount, added by. Day totals + grand total.
    """
    start = sql_date(parse_date(start_date))
    end = sql_date(parse_date(end_date))
    query = f"""
        SELECT DATE(re.created_at) AS entry_day,
               s.name AS supplier_name, p.name AS party_name,
               re.bill_number, re.register_date, re.amount,
               COALESCE(u.full_name, '-') AS added_by
        FROM register_entry re
        LEFT JOIN supplier s ON re.supplier_id = s.id
        LEFT JOIN party p ON re.party_id = p.id
        LEFT JOIN users u ON re.created_by = u.id
        WHERE DATE(re.created_at) >= '{start}' AND DATE(re.created_at) <= '{end}'
        {_id_filter('re.supplier_id', supplier_ids, supplier_all)}
        {_id_filter('re.party_id', party_ids, party_all)}
        ORDER BY DATE(re.created_at), s.name, p.name, re.bill_number
    """
    rows = execute_query(query)['result']

    data = _base('Bills Added Report', start, end)
    grand_total = 0
    grand_count = 0
    current_day: Optional[str] = None
    current_heading: Optional[Dict] = None
    subheadings_by_supplier: Dict[str, Dict] = {}

    def close_day():
        if current_heading is None:
            return
        day_total = 0
        for sub in current_heading['subheadings']:
            sub_total = sum(r['_amount'] for r in sub['dataRows'])
            sub['specialRows'] = [_total_row('Total (=) ', sub_total, 'amount')]
            day_total += sub_total
            for r in sub['dataRows']:
                r['amount'] = _fmt(r.pop('_amount'))
        current_heading['cumulative'] = {'name': 'Day Total', 'value': _fmt(day_total)}
        data['headings'].append(current_heading)

    for row in rows:
        day = _fmt_date(row['entry_day'])
        if day != current_day:
            close_day()
            current_day = day
            current_heading = {'title': f'Entered on {day}', 'subheadings': []}
            subheadings_by_supplier = {}
        supplier = row['supplier_name'] or '-'
        if supplier not in subheadings_by_supplier:
            sub = {'title': supplier, 'dataRows': [], 'specialRows': [], 'displayOnIndex': True}
            subheadings_by_supplier[supplier] = sub
            current_heading['subheadings'].append(sub)
        amount = int(row['amount'] or 0)
        subheadings_by_supplier[supplier]['dataRows'].append({
            'party': row['party_name'] or '-',
            'bill_no': row['bill_number'],
            'bill_date': _fmt_date(row['register_date']),
            'amount': None,  # replaced when the day closes
            '_amount': amount,
            'added_by': row['added_by'],
        })
        grand_total += amount
        grand_count += 1
    close_day()

    if grand_count:
        data['headings'].append({
            'title': 'Grand Total',
            'subheadings': [{
                'title': '',
                'dataRows': [{'bills_entered': grand_count, 'total_amount': _fmt(grand_total)}],
                'specialRows': [],
                'displayOnIndex': False,
            }],
        })
    return data


def _sale_summary(group: str, supplier_ids: List[int], party_ids: List[int],
                  start_date: str, end_date: str,
                  supplier_all: bool, party_all: bool) -> Dict:
    """Shared implementation for supplier_wise_sale / buyer_wise_sale."""
    is_supplier = group == 'supplier'
    entity_table = 's' if is_supplier else 'p'
    title = 'Supplier Wise Sale' if is_supplier else 'Buyer Wise Sale'
    name_col = 'supplier' if is_supplier else 'buyer'
    start = sql_date(parse_date(start_date))
    end = sql_date(parse_date(end_date))
    query = f"""
        SELECT {entity_table}.name AS entity_name,
               COUNT(re.id) AS bills,
               COALESCE(SUM(re.amount), 0) AS gross_amt,
               COALESCE(SUM(re.gr_amount), 0) AS gr_amt,
               COALESCE(SUM(re.deduction), 0) AS deduction,
               COALESCE(SUM(re.amount - re.gr_amount - re.deduction), 0) AS net_amt
        FROM register_entry re
        LEFT JOIN supplier s ON re.supplier_id = s.id
        LEFT JOIN party p ON re.party_id = p.id
        WHERE re.register_date >= '{start}' AND re.register_date <= '{end}'
        {_id_filter('re.supplier_id', supplier_ids, supplier_all)}
        {_id_filter('re.party_id', party_ids, party_all)}
        GROUP BY {entity_table}.name
        ORDER BY {entity_table}.name
    """
    rows = execute_query(query)['result']

    data = _base(title, start, end)
    data_rows = []
    totals = {'bills': 0, 'gross_amt': 0, 'gr_amt': 0, 'deduction': 0, 'net_amt': 0}
    for row in rows:
        for key in totals:
            totals[key] += int(row[key] or 0)
        data_rows.append({
            name_col: row['entity_name'] or '-',
            'bills': int(row['bills'] or 0),
            'gross_amt': _fmt(row['gross_amt']),
            'gr_amt': _fmt(row['gr_amt']),
            'deduction': _fmt(row['deduction']),
            'net_amt': _fmt(row['net_amt']),
        })
    if data_rows:
        special = [_total_row('Total (=) ', totals[col], col)
                   for col in ('gross_amt', 'gr_amt', 'deduction', 'net_amt')]
        data['headings'].append({
            'title': title,
            'subheadings': [{'title': '', 'dataRows': data_rows,
                             'specialRows': special, 'displayOnIndex': False}],
            'cumulative': {'name': 'Net Sale', 'value': _fmt(totals['net_amt'])},
        })
    return data


def supplier_wise_sale(supplier_ids, party_ids, start_date, end_date,
                       supplier_all=False, party_all=False) -> Dict:
    return _sale_summary('supplier', supplier_ids, party_ids, start_date, end_date,
                         supplier_all, party_all)


def buyer_wise_sale(supplier_ids, party_ids, start_date, end_date,
                    supplier_all=False, party_all=False) -> Dict:
    return _sale_summary('party', supplier_ids, party_ids, start_date, end_date,
                         supplier_all, party_all)


def supplier_wise_outstanding(supplier_ids: List[int], party_ids: List[int],
                              start_date: str, end_date: str,
                              supplier_all: bool = False, party_all: bool = False) -> Dict:
    """
    Unsettled bills (pending amount > 0) grouped per supplier, with ageing in days.
    The date range filters on the bill date.
    """
    start = sql_date(parse_date(start_date))
    end = sql_date(parse_date(end_date))
    query = f"""
        SELECT s.name AS supplier_name, p.name AS party_name,
               re.bill_number, re.register_date, re.amount,
               (re.amount - re.gr_amount - re.deduction - re.partial_amount) AS pending_amt,
               (CURRENT_DATE - re.register_date::date) AS days_old
        FROM register_entry re
        LEFT JOIN supplier s ON re.supplier_id = s.id
        LEFT JOIN party p ON re.party_id = p.id
        WHERE re.status != 'F'
          AND (re.amount - re.gr_amount - re.deduction - re.partial_amount) > 0
          AND re.register_date >= '{start}' AND re.register_date <= '{end}'
        {_id_filter('re.supplier_id', supplier_ids, supplier_all)}
        {_id_filter('re.party_id', party_ids, party_all)}
        ORDER BY s.name, p.name, re.register_date, re.bill_number
    """
    rows = execute_query(query)['result']

    data = _base('Supplier Wise Outstanding Bills', start, end)
    grand_pending = 0
    grand_count = 0
    current_supplier: Optional[str] = None
    current_heading: Optional[Dict] = None

    def close_supplier():
        if current_heading is None:
            return
        sub = current_heading['subheadings'][0]
        bill_total = sum(r['_bill'] for r in sub['dataRows'])
        pending_total = sum(r['_pending'] for r in sub['dataRows'])
        for r in sub['dataRows']:
            r['bill_amt'] = _fmt(r.pop('_bill'))
            r['pending_amt'] = _fmt(r.pop('_pending'))
        sub['specialRows'] = [
            _total_row('Total (=) ', bill_total, 'bill_amt'),
            _total_row('Pending (=) ', pending_total, 'pending_amt'),
        ]
        current_heading['cumulative'] = {'name': 'Outstanding', 'value': _fmt(pending_total)}
        data['headings'].append(current_heading)

    for row in rows:
        supplier = row['supplier_name'] or '-'
        if supplier != current_supplier:
            close_supplier()
            current_supplier = supplier
            current_heading = {
                'title': supplier,
                'subheadings': [{'title': '', 'dataRows': [], 'specialRows': [],
                                 'displayOnIndex': False}],
            }
        pending = int(row['pending_amt'] or 0)
        bill_amount = int(row['amount'] or 0)
        current_heading['subheadings'][0]['dataRows'].append({
            'party': row['party_name'] or '-',
            'bill_no': row['bill_number'],
            'bill_date': _fmt_date(row['register_date']),
            'days_old': int(row['days_old'] or 0),
            'bill_amt': None,
            'pending_amt': None,
            '_bill': bill_amount,
            '_pending': pending,
        })
        grand_pending += pending
        grand_count += 1
    close_supplier()

    if grand_count:
        data['headings'].append({
            'title': 'Grand Total',
            'subheadings': [{
                'title': '',
                'dataRows': [{'pending_bills': grand_count, 'total_outstanding': _fmt(grand_pending)}],
                'specialRows': [],
                'displayOnIndex': False,
            }],
        })
    return data


def local_dispatch_summary(supplier_ids: List[int], party_ids: List[int],
                           start_date: str, end_date: str,
                           supplier_all: bool = False, party_all: bool = False,
                           transport: Optional[str] = None) -> Dict:
    """
    Local party bills dispatched from the office, grouped by dispatch day.
    Mirrors the physical Dispatch Pad. One row per dispatched bill with:
    Bill No, Bill Date, Party, Supplier, L.R. No., Transport, No. of Bills
    (count within its dispatch slip), Dispatch Date and User (who recorded it).

    Sources (unioned, de-duplicated):
      1. Dispatch Pad slips (dispatch / dispatch_bill), grouped by dispatch date.
      2. Register entries with an L.R. No. or transport filled in directly on the
         bill, grouped by the day the entry was recorded (created_at).

    Filters: date range (grouping day), party (party_ids), supplier, transport.
    """
    start = sql_date(parse_date(start_date))
    end = sql_date(parse_date(end_date))

    def transport_clause(col: str) -> str:
        if not transport:
            return ''
        safe = str(transport).replace("'", "''")
        return f" AND {col} ILIKE '%{safe}%'"

    query = f"""
        SELECT * FROM (
            -- 1. Dispatch Pad slips
            SELECT d.dispatch_date AS day_date,
                   d.serial_number AS serial_number,
                   p.name AS party_name,
                   s.name AS supplier_name,
                   db.bill_number AS bill_number,
                   db.bill_date AS bill_date,
                   db.lr_number AS lr_number,
                   db.transport_name AS transport_name,
                   COALESCE(u.full_name, '-') AS user_name,
                   cnt.bills_in_dispatch AS num_bills,
                   0 AS src_order
            FROM dispatch_bill db
            JOIN dispatch d ON db.dispatch_id = d.id
            LEFT JOIN party p ON d.party_id = p.id
            LEFT JOIN supplier s ON db.supplier_id = s.id
            LEFT JOIN users u ON d.created_by = u.id
            JOIN (SELECT dispatch_id, COUNT(*) AS bills_in_dispatch
                  FROM dispatch_bill GROUP BY dispatch_id) cnt
                  ON cnt.dispatch_id = d.id
            WHERE d.dispatch_date >= '{start}' AND d.dispatch_date <= '{end}'
            {_id_filter('d.party_id', party_ids, party_all)}
            {_id_filter('db.supplier_id', supplier_ids, supplier_all)}
            {transport_clause('db.transport_name')}

            UNION ALL

            -- 2. Register entries with dispatch details filled on the bill
            SELECT DATE(re.created_at) AS day_date,
                   CAST(NULL AS INTEGER) AS serial_number,
                   p.name AS party_name,
                   s.name AS supplier_name,
                   re.bill_number AS bill_number,
                   re.register_date AS bill_date,
                   re.lr_number AS lr_number,
                   re.transport_name AS transport_name,
                   COALESCE(u.full_name, '-') AS user_name,
                   COUNT(*) OVER (PARTITION BY DATE(re.created_at), re.party_id) AS num_bills,
                   1 AS src_order
            FROM register_entry re
            LEFT JOIN party p ON re.party_id = p.id
            LEFT JOIN supplier s ON re.supplier_id = s.id
            LEFT JOIN users u ON re.created_by = u.id
            WHERE (re.lr_number IS NOT NULL OR re.transport_name IS NOT NULL)
              AND re.id NOT IN (SELECT register_entry_id FROM dispatch_bill
                                WHERE register_entry_id IS NOT NULL)
              AND DATE(re.created_at) >= '{start}' AND DATE(re.created_at) <= '{end}'
            {_id_filter('re.party_id', party_ids, party_all)}
            {_id_filter('re.supplier_id', supplier_ids, supplier_all)}
            {transport_clause('re.transport_name')}
        ) combined
        ORDER BY day_date, src_order, serial_number NULLS LAST, bill_number
    """
    rows = execute_query(query)['result']

    data = _base('Local Dispatch Summary', start, end)
    grand_bills = 0
    current_day: Optional[str] = None
    current_heading: Optional[Dict] = None

    def close_day():
        if current_heading is not None:
            sub = current_heading['subheadings'][0]
            sub['specialRows'] = [
                {'name': 'Bills (=) ', 'value': str(len(sub['dataRows'])),
                 'column': 'bill_no', 'beforeData': False},
            ]
            current_heading['cumulative'] = {'name': 'Bills Dispatched',
                                             'value': str(len(sub['dataRows']))}
            data['headings'].append(current_heading)

    for row in rows:
        day = _fmt_date(row['day_date'])
        if day != current_day:
            close_day()
            current_day = day
            current_heading = {
                'title': f'Dispatched on {day}',
                'subheadings': [{'title': '', 'dataRows': [], 'specialRows': [],
                                 'displayOnIndex': True}],
            }
        current_heading['subheadings'][0]['dataRows'].append({
            'bill_no': row['bill_number'],
            'bill_date': _fmt_date(row['bill_date']),
            'party': row['party_name'] or '-',
            'supplier': row['supplier_name'] or '-',
            'lr_no': row['lr_number'] or '-',
            'transport': row['transport_name'] or '-',
            'num_bills': int(row['num_bills'] or 0),
            'dispatch_date': day,
            'user': row['user_name'],
        })
        grand_bills += 1
    close_day()

    if grand_bills:
        data['headings'].append({
            'title': 'Grand Total',
            'subheadings': [{
                'title': '',
                'dataRows': [{'total_bills_dispatched': grand_bills}],
                'specialRows': [],
                'displayOnIndex': False,
            }],
        })
    return data


CUSTOM_REPORTS = {
    'bills_added_report': bills_added_report,
    'supplier_wise_sale': supplier_wise_sale,
    'buyer_wise_sale': buyer_wise_sale,
    'supplier_wise_outstanding': supplier_wise_outstanding,
    'local_dispatch_summary': local_dispatch_summary,
}

from typing import Dict, List, Union
from API_Database import retrieve_register_entry, retrieve_memo_entry
from Reports import table

class PaymentList(table.HeaderSubheaderTable):

    def __init__(self) -> None:
        """Initializes the Payment List report with a preset title."""
        super().__init__('Payment List')

    def generate_cumulative(self, header_ids: Union[int, List[int]], subheader_ids: Union[int, List[int]], start_date: str, end_date: str, supplier_all: bool=False, party_all: bool=False):
        """
        Generate cumulative totals for Payment List with optimized bulk operations.
        Uses bulk queries when all suppliers/parties are selected.
        """
        try:
            input_args = self._generate_input_args(header_ids, subheader_ids, start_date, end_date, force_list_args=True)
            input_args['supplier_all'] = supplier_all
            input_args['party_all'] = party_all
            total_pending_amount = retrieve_register_entry.generate_total(**input_args, column_name='amount', pending=True)
            total_part = retrieve_memo_entry.generate_memo_total(**input_args, memo_type='PR')
            pending = total_pending_amount - total_part
            return {'name': 'Total Pending', 'value': self._format_indian_currency(pending)}
        except Exception as e:
            print(f'Error in generate_cumulative: {str(e)}')
            return {'name': 'Total Pending', 'value': self._format_indian_currency(0)}

    def generate_total_rows(self, data_rows: Dict, before_data: bool=False):
        """
        Generate total rows for Payment List with optimized calculations.
        Uses a single pass through data with dictionary-based totals.
        """
        total_rows = []
        totals = {'bill_amt': {'total': 0, 'under_sixty': 0, 'above_sixty': 0, 'above_one_twenty': 0}, 'part_amt': {'total': 0}}
        try:
            for row in data_rows:
                if 'bill_amt' in row:
                    value = str(row['bill_amt']).replace(',', '') if row['bill_amt'] != '' else '0'
                    amount = int(value)
                    totals['bill_amt']['total'] += amount
                    if 'days' in row:
                        days = int(row['days'])
                        if days <= 60:
                            totals['bill_amt']['under_sixty'] += amount
                        elif days <= 120:
                            totals['bill_amt']['above_sixty'] += amount
                        else:
                            totals['bill_amt']['above_one_twenty'] += amount
                if 'part_amt' in row:
                    value = str(row['part_amt']).replace(',', '') if row['part_amt'] != '' else '0'
                    amount = int(value)
                    totals['part_amt']['total'] += amount
            if 'part_amt' in self.total_rows_columns:
                total_rows.append(self._total_row_dict('Total (=)', totals['part_amt']['total'], 'part_amt', before_data))
            if 'bill_amt' in self.total_rows_columns:
                total_rows.extend([
                                    self._total_row_dict('Subtotal (=)', totals['bill_amt']['total'], 'bill_amt', before_data),
                                   self._total_row_dict('>120 days (+)', totals['bill_amt']['above_one_twenty'], 'bill_amt', before_data), 
                                   self._total_row_dict('60-120 days (+)', totals['bill_amt']['above_sixty'], 'bill_amt', before_data), 
                                   self._total_row_dict('<60 days (+)', totals['bill_amt']['under_sixty'], 'bill_amt', before_data)
                                  ])
                if 'part_amt' in self.total_rows_columns:
                    pending_amt = totals['bill_amt']['total'] - totals['part_amt']['total']
                    total_rows.extend([self._total_row_dict('Part (-)', totals['part_amt']['total'], 'bill_amt', before_data, negative=True), self._total_row_dict('Pending (=)', pending_amt, 'bill_amt', before_data)])
        except Exception as e:
            print(f'Error in generate_total_rows: {str(e)}')
        return total_rows
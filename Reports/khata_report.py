from typing import Dict
from Reports import table

class KhataReport(table.HeaderSubheaderTable):

    def __init__(self) -> None:
        """Initializes the Khata Report with a preset title."""
        super().__init__('Khata Report')

    def generate_total_rows(self, data_rows: Dict, before_data: bool=False):
        """
        Generate total rows for Khata Report with optimized calculations.
        ASSUMPTION: "memo_amt" total must show decreased GR and LESS values and then show total value
        ASSUMPTION: "bill_amt" total must remove total GR and LESS in them and then show pending value
        """
        total_rows = []
        totals = {column: 0 for column in self.total_rows_columns}
        memo_totals = {'total': 0, 'gr': 0, 'less': 0, 'settlement': 0}
        try:
            for row in data_rows:
                for column in self.total_rows_columns:
                    if column in row:
                        value = str(row[column]).replace(',', '') if row[column] != '' else '0'
                        amount = int(value)
                        totals[column] += amount
                        if column == 'memo_amt' and 'memo_type' in row:
                            memo_totals['total'] += amount
                            if row['memo_type'] == 'G':
                                memo_totals['gr'] += amount
                            elif row['memo_type'] == 'D':
                                memo_totals['less'] += amount
                            elif row['memo_type'] == 'ST':
                                memo_totals['settlement'] += amount
            for column in self.total_rows_columns:
                total = totals[column]
                total_rows.append(self._total_row_dict('Subtotal', total, column, before_data))
                if column == 'memo_amt':
                    memo_total_without_settlement = memo_totals['total'] - memo_totals['settlement']
                    gr_percent = memo_totals['gr'] / memo_total_without_settlement * 100 if memo_total_without_settlement else 0
                    less_percent = memo_totals['less'] / memo_total_without_settlement * 100 if memo_total_without_settlement else 0
                    settlement_percent = memo_totals['settlement'] / memo_totals['total'] * 100 if memo_totals['total'] else 0
                    
                    total_paid = memo_totals['total'] - memo_totals['gr'] - memo_totals['less'] - memo_totals['settlement']
                    
                    total_rows.extend([
                        self._total_row_dict(f'{gr_percent:.2f}% GR (-)', memo_totals['gr'], column, before_data, negative=True),
                        self._total_row_dict(f'{less_percent:.2f}% Less (-)', memo_totals['less'], column, before_data, negative=True),
                        self._total_row_dict(f'{settlement_percent:.2f}% Settlement (-)', memo_totals['settlement'], column, before_data, negative=True),
                        self._total_row_dict('Total Paid (=)', total_paid, column, before_data)
                    ])
            if 'bill_amt' in totals and 'memo_amt' in totals:
                memo_total_without_settlement = memo_totals['total'] - memo_totals['settlement']
                pending_amt = totals['bill_amt'] - memo_total_without_settlement
                total_rows.extend([
                    self._total_row_dict('Paid+GR (-)', memo_total_without_settlement, 'bill_amt', before_data, negative=True),
                    self._total_row_dict('Pending (=)', pending_amt, 'bill_amt', before_data)
                ])
        except Exception as e:
            print(f'Error in generate_total_rows: {str(e)}')
        return total_rows

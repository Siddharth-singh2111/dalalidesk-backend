from __future__ import annotations
from typing import List, Dict, Union
from datetime import datetime
from Individual import Supplier, Party
from API_Database import efficiency, parse_date
from API_Database import retrieve_register_entry, retrieve_partial_payment, retrieve_order_form, retrieve_memo_settlement_rows
from itertools import zip_longest

class MetaTable:
    _preset = {'Khata Report': {'header_entity': Party, 'subheader_entity': Supplier, 'data_rows': retrieve_register_entry.get_khata_data_by_date, 'data_rows_bulk': retrieve_register_entry.get_khata_data_by_date_bulk, 'numeric_columns': ['bill_amt', 'memo_amt', 'chk_amt'], 'total_rows_columns': ['bill_amt', 'memo_amt'], 'part_display_mode': 'row'}, 'Supplier Register': {'header_entity': Supplier, 'subheader_entity': Party, 'data_rows': retrieve_register_entry.get_supplier_register_data, 'data_rows_bulk': retrieve_register_entry.get_supplier_register_data_bulk, 'numeric_columns': ['bill_amt', 'pending_amt'], 'total_rows_columns': ['bill_amt', 'pending_amt'], 'part_display_mode': 'none'}, 'Payment List': {'header_entity': Party, 'subheader_entity': Supplier, 'data_rows': retrieve_register_entry.get_payment_list_data, 'data_rows_bulk': retrieve_register_entry.get_payment_list_data_bulk, 'numeric_columns': ['bill_amt', 'part_amt'], 'total_rows_columns': ['part_amt', 'bill_amt'], 'part_display_mode': 'column'}, 'Order Form': {'header_entity': Supplier, 'subheader_entity': Party, 'data_rows': retrieve_order_form.get_order_form_report_data, 'data_rows_bulk': None, 'numeric_columns': ['order_no'], 'total_rows_columns': [], 'part_display_mode': 'none'}}

    def __init__(self, title: str) -> None:
        self.title = title
        self.header_entity = self._preset[title]['header_entity']
        self.subheader_entity = self._preset[title]['subheader_entity']
        self.filter_subheader = efficiency.filter_out_parties if self.header_entity is Supplier else efficiency.filter_out_supplier
        self.data_rows = self._preset[title]['data_rows']
        self.data_rows_bulk = self._preset[title]['data_rows_bulk']
        self.numeric_columns = self._preset[title]['numeric_columns']
        self.total_rows_columns = self._preset[title]['total_rows_columns']
        self.part_display_mode = self._preset[title]['part_display_mode']
        self.header_supplier = True if self.header_entity is Supplier else False

    def generate_data_rows_bulk(self, header_ids: List[int], subheader_ids: List[int], start_date: str, end_date: str, supplier_all: bool=False, party_all: bool=False) -> tuple[List[Dict], List[Dict], Dict]:
        """
        Generate data rows for multiple headers and subheaders in one query.
        Returns (data_rows, special_rows, cumulatives) where cumulatives contains both header and subheader totals.
        """
        if not self.data_rows_bulk:
            raise NotImplementedError('Bulk data fetching not implemented for this report type')
        try:
            input_args = self._generate_input_args(header_ids, subheader_ids, start_date, end_date)
            input_args['supplier_all'] = supplier_all
            input_args['party_all'] = party_all
            print('Fetching bulk data rows...')
            data_rows = self.data_rows_bulk(**input_args)
            part_args = {**input_args}
            if 'supplier_id' in part_args:
                part_args['supplier_ids'] = [part_args.pop('supplier_id')]
            if 'party_id' in part_args:
                part_args['party_ids'] = [part_args.pop('party_id')]
            print('Fetching part data...')
            if self.part_display_mode == 'column':
                part_data = self.generate_part_columns_bulk(**part_args)
            elif self.part_display_mode == 'row':
                part_data = self.generate_part_rows_bulk(**part_args)
                if self.title == 'Khata Report':
                    part_data.extend(self.generate_settlement_rows_bulk(**part_args))
            else:
                part_data = []
            print('Grouping part data...')
            grouped_part_data = {}
            for part in part_data:
                header_id = part.pop('supplier_id') if self.header_supplier else part.pop('party_id')
                subheader_id = part.pop('party_id') if self.header_supplier else part.pop('supplier_id')
                if header_id and subheader_id:
                    if header_id not in grouped_part_data:
                        grouped_part_data[header_id] = {}
                    if subheader_id not in grouped_part_data[header_id]:
                        grouped_part_data[header_id][subheader_id] = []
                    grouped_part_data[header_id][subheader_id].append(part)
            print('Grouping Data Rows')
            grouped_data = {}
            previous_header_id = None
            previous_subheader_id = None
            for row in data_rows:
                header_id = row.get('header_id') or previous_header_id
                subheader_id = row.get('subheader_id') or previous_subheader_id
                if header_id is not None:
                    previous_header_id = header_id
                if subheader_id is not None:
                    previous_subheader_id = subheader_id
                if header_id not in grouped_data:
                    grouped_data[header_id] = {}
                if subheader_id not in grouped_data[header_id]:
                    grouped_data[header_id][subheader_id] = []
                grouped_data[header_id][subheader_id].append(row)
            print('Generating Cumulatives...')
            cumulatives = {'headers': {}, 'subheaders': {}}
            processed_rows = []
            for header_id in grouped_data:
                header_data = []
                for (subheader_id, subheader_data) in grouped_data[header_id].items():
                    subheader_key = f'{header_id}_{subheader_id}'
                    try:
                        cumulative = self.generate_cumulative(header_id, subheader_id, start_date, end_date, supplier_all=False, party_all=False)
                        if cumulative:
                            cumulatives['subheaders'][subheader_key] = cumulative
                    except Exception as e:
                        print(f'Error calculating subheader cumulative: {str(e)}')
                    processed_rows.extend(subheader_data)
                    header_data.extend(subheader_data)
                try:
                    cumulative = self.generate_cumulative(header_id, subheader_ids, start_date, end_date, supplier_all=False, party_all=False)
                    if cumulative:
                        cumulatives['headers'][header_id] = cumulative
                except Exception as e:
                    print(f'Error calculating header cumulative: {str(e)}')
            total_rows = []
            print('Done with table.py')
            return (processed_rows, grouped_part_data, total_rows, cumulatives)
        except Exception as e:
            print(f'Error in generate_data_rows_bulk: {str(e)}')
            return ([], [], {})

    def generate_total_rows(self, data_rows: Dict, before_data: bool=False):
        """
        Generate total values for certain columns
        """
        raise NotImplementedError

    def generate_cumulative(self, header_ids: Union[List[int], int], subheader_ids: Union[List[int], int], start_date: str, end_date: str, supplier_all: bool=False, party_all: bool=False):
        """
        Generate cumulative values for certain columns.
        Supports bulk operations with all flags.
        """
        return {}

    def generate_part_rows(self, supplier_id: int, party_id: int, **kwargs):
        """
        Generate part rows for a given header and subheader
        """
        return retrieve_partial_payment.get_partial_payment(supplier_id, party_id)

    def generate_settlement_rows(self, supplier_id: int, party_id: int, **kwargs):
        """
        Generate settlement rows for a given header and subheader
        """
        return retrieve_memo_settlement_rows.get_memo_settlement(supplier_id, party_id)

    def generate_part_rows_bulk(self, supplier_ids: List[int], party_ids: List[int], supplier_all: bool=False, party_all: bool=False, **kwargs):
        """
        Generate part rows for multiple headers and subheaders in bulk.
        Uses optimized bulk query when all flags are set.
        """
        return retrieve_partial_payment.get_partial_payment_bulk(supplier_ids, party_ids, supplier_all=supplier_all, party_all=party_all)
        
    def generate_settlement_rows_bulk(self, supplier_ids: List[int], party_ids: List[int], supplier_all: bool=False, party_all: bool=False, **kwargs):
        """
        Generate settlement rows for multiple headers and subheaders in bulk.
        Uses optimized bulk query when all flags are set.
        """
        return retrieve_memo_settlement_rows.get_memo_settlement_bulk(supplier_ids, party_ids, supplier_all=supplier_all, party_all=party_all)

    def generate_part_columns_bulk(self, supplier_ids: List[int], party_ids: List[int], supplier_all: bool=False, party_all: bool=False, **kwargs):
        """
        Generate part columns for multiple headers and subheaders in bulk.
        Uses optimized bulk query when all flags are set.
        """
        part_data = self.generate_part_rows_bulk(supplier_ids, party_ids, supplier_all=supplier_all, party_all=party_all, **kwargs)
        part_columns = []
        for part in part_data:
            part_column = {'supplier_id': part['supplier_id'], 'party_id': part['party_id']}
            for part_key in part:
                if part_key == 'memo_no':
                    part_column['part_no'] = part[part_key]
                elif part_key == 'memo_date':
                    part_column['part_date'] = part[part_key]
                elif part_key == 'memo_amt':
                    part_column['part_amt'] = part[part_key]
            part_columns.append(part_column)
        return part_columns

    def _generate_special_row(self, entity_name: str, value: str, column: str, before_data: bool=False):
        """Generates a special row dictionary for an entity using a value and column, with optional formatting."""
        return {'name': entity_name, 'value': self._format_indian_currency(value), 'column': column, 'beforeData': before_data}

    def _total_row_dict(self, name: str, numeric: int, column: str, before_data: bool, negative: bool=False):
        """Creates a dictionary representing a total row with a formatted value and column information."""
        value = self._format_indian_currency(numeric, negative=negative)
        return {'name': name, 'value': value, 'column': column, 'numeric': numeric, 'beforeData': before_data}

    def _generate_input_args(self, header_ids: Union[List[int], int], subheader_ids: Union[List[int], int], start_date: str, end_date: str, force_list_args: bool=False, force_int_args: bool=False):
        """
        Function to map header and subheader ids to party_id and supplier_id
        """
        if force_int_args or (isinstance(header_ids, int) and isinstance(subheader_ids, int) and (not force_list_args)):
            input_args = {'party_id' if self.header_entity is Party else 'supplier_id': header_ids, 'supplier_id' if self.subheader_entity is Supplier else 'party_id': subheader_ids, 'start_date': start_date, 'end_date': end_date}
        else:
            input_args = {'party_ids' if self.header_entity is Party else 'supplier_ids': header_ids, 'supplier_ids' if self.subheader_entity is Supplier else 'party_ids': subheader_ids, 'start_date': start_date, 'end_date': end_date}
        return input_args

    @staticmethod
    def _format_indian_currency(number, negative: bool=False):
        """Formats a number into the Indian currency format; prepends a negative sign if specified."""
        (s, *d) = str(number).partition('.')
        r = ','.join([s[x - 2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
        if negative:
            return ''.join(['- ', r] + d)
        return ''.join([r] + d)

    @staticmethod
    def merge_dicts_parallel(dict_a, dict_b):
        """Merges two lists of dictionaries in parallel, removing duplicate keys from the second list."""
        merged_dicts = []
        for (dict_a_i, dict_b_i) in zip_longest(dict_a, dict_b, fillvalue={}):
            for key in dict_a_i:
                if key in dict_b_i:
                    if dict_b_i[key] is not None and dict_b_i[key] != '':
                        print(f'WARNING: Duplicate key {key} in second dict is removed in merge_dicts_parallel')
                    dict_b_i.pop(key)
            merged_dict = {**dict_a_i, **dict_b_i}
            merged_dicts.append(merged_dict)
        return merged_dicts

    @staticmethod
    def _format_date(date: datetime) -> str:
        """Formats a datetime object or date string into DD/MM/YYYY format."""
        if not isinstance(date, datetime):
            date = parse_date(date)
        return date.strftime('%d/%m/%Y')

class HeaderSubheaderTable(MetaTable):

    def __init__(self, title: str) -> None:
        super().__init__(title)

    def generate_data_rows(self, header_id: int, subheader_id: int, start_date: str, end_date: str, supplier_all: bool=False, party_all: bool=False) -> tuple[List[Dict], List[Dict]]:
        """
        Generate data rows for a given header and subheader
        """
        input_args = self._generate_input_args(header_id, subheader_id, start_date, end_date)
        input_args['supplier_all'] = supplier_all
        input_args['party_all'] = party_all
        data_rows = self.data_rows(**input_args)
        part_args = {**input_args}
        if 'supplier_id' in part_args:
            part_args['supplier_ids'] = [part_args.pop('supplier_id')]
        if 'party_id' in part_args:
            part_args['party_ids'] = [part_args.pop('party_id')]
        if self.part_display_mode == 'column':
            data_rows = self.merge_dicts_parallel(self.generate_part_columns_bulk(**part_args), data_rows)
        elif self.part_display_mode == 'row':
            data_rows.extend(self.generate_part_rows_bulk(**part_args))
            # Add settlement rows after part rows
            data_rows.extend(self.generate_settlement_rows_bulk(**part_args))
        total_rows = self.generate_total_rows(data_rows)
        cumulative = self.generate_cumulative(header_id, subheader_id, start_date, end_date)
        for row in data_rows:
            for column in self.numeric_columns:
                try:
                    if column in row:
                        row[column] = self._format_indian_currency(row[column])
                except:
                    print(f'Error in formatting column {column} in row {row} to Indian Currency')
        return (data_rows, total_rows, cumulative)

    def generate_part_columns(self, supplier_id: int, party_id: int, **kwargs):
        """
        Generate part columns for a given header and subheader
        """
        part_data = self.generate_part_rows(supplier_id, party_id)
        part_columns = []
        for part in part_data:
            part_column = {}
            for part_key in part:
                if part_key == 'memo_no':
                    part_column['part_no'] = part[part_key]
                elif part_key == 'memo_date':
                    part_column['part_date'] = part[part_key]
                elif part_key == 'memo_amt':
                    part_column['part_amt'] = part[part_key]
            part_columns.append(part_column)
        return part_columns

class HeaderTable(MetaTable):

    def __init__(self, title: str) -> None:
        super().__init__(title)

    def generate_data_rows(self, header_id: int, subheader_ids: int, start_date: str, end_date: str, supplier_all: bool=False, party_all: bool=False) -> tuple[List[Dict], List[Dict]]:
        """
        Generate data rows for a given header and subheader
        """
        data_rows = []
        for subheader_id in subheader_ids:
            input_args = self._generate_input_args(header_id, subheader_id, start_date, end_date)
            input_args['supplier_all'] = supplier_all
            input_args['party_all'] = party_all
            register_data = self.data_rows(**input_args)
            if self.header_entity is Party:
                for register in register_data:
                    if 'party_name' in register:
                        register.pop('party_name')
            elif self.header_entity is Supplier:
                for register in register_data:
                    if 'supplier_name' in register:
                        register.pop('supplier_name')
            data_rows.extend(register_data)
        part_args = {**input_args}
        if 'supplier_id' in part_args:
            part_args['supplier_ids'] = [part_args.pop('supplier_id')]
        if 'party_id' in part_args:
            part_args['party_ids'] = [part_args.pop('party_id')]
        if self.part_display_mode == 'column':
            data_rows = self.merge_dicts_parallel(self.generate_part_columns_bulk(**part_args), data_rows)
        elif self.part_display_mode == 'row':
            data_rows.extend(self.generate_part_rows_bulk(**part_args))
            # Add settlement rows after part rows
            data_rows.extend(self.generate_settlement_rows_bulk(**part_args))
        total_rows = self.generate_total_rows(data_rows)
        for row in data_rows:
            for column in self.numeric_columns:
                try:
                    if column in row:
                        row[column] = self._format_indian_currency(row[column])
                except:
                    print(f'Error in formatting column {column} in row {row} to Indian Currency')
        cumulative = {}
        return (data_rows, total_rows, cumulative)

"""
==== Description ====
This class is used to represent a register entry. A register entry is made when
the bill for an order is received.

"""
from __future__ import annotations
from datetime import datetime
from typing import List, Dict, Union
from API_Database import insert_register_entry, update_register_entry, utils, get_register_entry_by_id
from API_Database import get_register_entry_id, get_register_entry
from API_Database import get_pending_bills, mark_order_forms_as_registered
from Exceptions import DataError
from Entities import Entry
from OCR import parse_register_entry
from .ItemEntry import ItemEntry

class RegisterEntry(Entry):
    """
    A class that represents a register entry


    ===Attributes===

    bill_number: a unique number that links a RegisterEntry to a MemoEntry
    amount: the amount for which the party has received an order
    date: the date when the bill is received
    supplier: the full name of the supplier
    party: the full name of the party

    """
    supplier_id: int
    party_id: int
    register_date: datetime
    amount: int
    bill_number: int
    status: str
    gr_amount: int
    deduction: int
    partial_amount: int
    _report_attribute_map = {'bill_number': 'bill_no', 'register_date': 'bill_date', 'amount': 'bill_amt', 'status': 'bill_status'}

    def __init__(self, bill_number: int, amount: int, supplier_id: int, party_id: int, register_date: Union[str, datetime], status: str='N', gr_amount: int=0, deduction: int=0, partial_amount: int=0, table_name='register_entry', *args, **kwargs) -> None:
        """Initializes a RegisterEntry with bill number, amount, supplier and party IDs, register date, status, and payment details."""
        super().__init__(*args, table_name=table_name, **kwargs)
        self.bill_number = bill_number
        self.amount = amount
        self.supplier_id = supplier_id
        self.party_id = party_id
        self.register_date = utils.sql_date(utils.parse_date(register_date))
        self.gr_amount = gr_amount
        self.deduction = deduction
        self.status = status
        self.partial_amount = partial_amount

    def get_pending_amount(self) -> int:
        """Calculates and returns the pending amount after subtracting gr_amount, deduction, and partial_amount from the total amount."""
        return int(self.amount - self.gr_amount - self.deduction - self.partial_amount)

    def update(self) -> Dict:
        """Updates the register entry in the database and returns the update status."""
        if insert_register_entry.check_new_register(self, edit_mode=True):
            return update_register_entry.update_register_entry_data(self)
        else:
            raise DataError({'status': 'error', 'message': 'Duplicate Bill Number', 'input_errors': {'bill_number': {'status': 'error', 'message': 'Bill number already exists in a seperate entry'}}})

    def get_id(self) -> int:
        """Returns the ID of the register entry; computes it if not already set."""
        super_id = super().get_id()
        if super_id is not None:
            return super_id
        return get_register_entry_id(self.supplier_id, self.party_id, self.bill_number, self.register_date)

    def delete(self) -> Dict:
        """Deletes the register entry and any associated item entries if unpaid; returns the deletion status."""
        if self.status == 'N':
            item_entries = ItemEntry.retrieve(register_entry_id=self.get_id())
            if isinstance(item_entries, list):
                [item_entry.delete() for item_entry in item_entries]
            else:
                item_entries.delete()
            return super().delete()
        else:
            return {'status': 'error', 'message': 'Register Entry has been paid'}

    @staticmethod
    def get_pending_bills(supplier_id: int, party_id: int) -> List[Dict]:
        pending_bills_data = get_pending_bills(supplier_id, party_id)
        return pending_bills_data

    @staticmethod
    def process_bill_image(image) -> Dict:
        """
        Process the image of a bill and return the extracted data
        IMPORTANT: image must be a base64 encoded string in jpeg format
        """
        return parse_register_entry(image)

    @classmethod
    def from_dict(cls, data: Dict, *args, **kwargs) -> RegisterEntry:
        """Creates a RegisterEntry instance from a dictionary, converting necessary fields to integers."""
        int_attributes = ['bill_number', 'amount', 'supplier_id', 'party_id', 'gr_amount', 'deduction', 'partial_amount']
        data = cls.convert_int_attributes(data, int_attributes)
        return cls(**data)

    @classmethod
    def retrieve(cls, supplier_id: int, party_id: int, bill_number: Union[List[Dict], int, str], register_date: Union[str, datetime]=None) -> Union[RegisterEntry, List[RegisterEntry]]:
        """
        Retrieve register entries.
        
        For single bill:
            bill_number: int or str - the bill number
            register_date: str or datetime - the register date (required)
            
        For multiple bills:
            bill_number: List[Dict] where each dict has:
                - 'bill_number': int or str
                - 'register_date': str or datetime
            register_date: ignored for multiple bills
        """
        if isinstance(bill_number, list):
            bills_data = []
            for bill_info in bill_number:
                bill_num = bill_info['bill_number']
                bill_date = utils.sql_date(utils.parse_date(bill_info['register_date']))
                bills_data.append(get_register_entry(supplier_id, party_id, bill_num, bill_date))
            return [cls.from_dict(d) for d in bills_data]
        if not register_date:
            raise ValueError('register_date is required for single bill retrieval')
        register_date = utils.sql_date(utils.parse_date(register_date))
        bill_data = get_register_entry(supplier_id, party_id, bill_number, register_date)
        return cls.from_dict(bill_data)

    @classmethod
    def retrieve_by_id(cls, id: int) -> RegisterEntry:
        """Retrieves a register entry by its ID and returns its details as a dictionary; raises DataError if not found or duplicated."""
        data = get_register_entry_by_id(id)
        return cls.from_dict(data)

    @classmethod
    def retrieve_by_id_list(cls, ids: List[int]) -> List[RegisterEntry]:
        """Retrieves multiple register entries by a list of IDs and returns them as a list of RegisterEntry instances."""
        register_entries = []
        for id in ids:
            register_entries.append(cls.retrieve_by_id(id))
        return register_entries

    @classmethod
    def insert(cls, data: Dict, get_cls: bool=False) -> Dict:
        """Inserts a new register entry into the database after validating uniqueness; returns the insertion status and optionally the instance."""
        register_entry = cls.from_dict(data)
        if insert_register_entry.check_new_register(register_entry):
            ret = insert_register_entry.insert_register_entry(register_entry)
            if ret['status'] == 'okay':
                mark_order_forms_as_registered(register_entry.supplier_id, register_entry.party_id)
            if get_cls and ret['status'] == 'okay':
                ret['class'] = register_entry
            return ret
        else:
            raise DataError({'status': 'error', 'message': 'Duplicate Bill Number', 'input_errors': {'bill_number': {'status': 'error', 'message': 'Bill number already exists'}}})
"""
==== Description ====
Represents a Credit/Debit Note recorded against a supplier<->party account
(standalone, not tied to a specific bill). A Credit note reduces the party's
outstanding amount; a Debit note increases it. Surfaced in the Khata report.
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, Union
from API_Database import insert_credit_debit_note, retrieve_credit_debit_note, utils
from Entities import Entry


class CreditDebitNote(Entry):
    """
    A credit or debit note between a supplier and a party.

    ===Attributes===
    note_type: 'Credit' or 'Debit'
    note_number: the note's own reference number (optional)
    note_date: the date on the note
    amount: the note amount
    supplier_id / party_id: the account the note belongs to
    remark: optional free-text reason
    """
    note_type: str
    note_number: int
    note_date: datetime
    amount: int
    supplier_id: int
    party_id: int
    remark: str

    def __init__(self, note_type: str, amount: int, supplier_id: int, party_id: int,
                 note_date: Union[str, datetime], note_number: int = None,
                 remark: str = None, table_name: str = 'credit_debit_note',
                 *args, **kwargs) -> None:
        """Initializes a CreditDebitNote with its type, amount, supplier/party and date."""
        super().__init__(*args, table_name=table_name, **kwargs)
        self.note_type = note_type
        self.amount = amount
        self.supplier_id = supplier_id
        self.party_id = party_id
        self.note_date = utils.sql_date(utils.parse_date(note_date))
        self.note_number = note_number
        self.remark = remark or None

    @classmethod
    def from_dict(cls, data: Dict, *args, **kwargs) -> CreditDebitNote:
        """Creates a CreditDebitNote from a dict, converting numeric fields to ints."""
        int_attributes = ['note_number', 'amount', 'supplier_id', 'party_id']
        data = cls.convert_int_attributes(data, int_attributes)
        return cls(**data)

    @classmethod
    def retrieve_by_id(cls, id: int) -> CreditDebitNote:
        """Retrieves a credit/debit note by its ID."""
        data = retrieve_credit_debit_note.get_credit_debit_note_by_id(id)
        return cls.from_dict(data)

    @classmethod
    def insert(cls, data: Dict, get_cls: bool = False) -> Dict:
        """Inserts a new credit/debit note and returns the insertion status.

        Rejects a duplicate: the same note number may not be saved twice for the
        same note type and supplier-party account.
        """
        note = cls.from_dict(data)
        if note.note_number is not None and retrieve_credit_debit_note.credit_debit_note_exists(
                note.note_type, note.note_number, note.supplier_id, note.party_id):
            return {
                'status': 'error',
                'message': f'Duplicate note number: a {note.note_type} note #{note.note_number} '
                           f'already exists for this supplier-party account.',
                'input_errors': {
                    'note_number': {
                        'error': True,
                        'message': f'A {note.note_type} note #{note.note_number} already exists for this account.',
                    }
                },
            }
        ret = insert_credit_debit_note.insert_credit_debit_note(note)
        if get_cls and ret.get('status') == 'okay':
            ret['class'] = note
        return ret

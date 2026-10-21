from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime, date
from pydantic import Field, field_validator
from .base import BaseSchema
from .user import UserSchema
import json

class TdsDetailSchema(BaseSchema):
    id: Optional[int] = None
    amount: float
    notes: Optional[str] = None
    checked: Optional[bool] = False
    dalali_id: Optional[int] = None

class DalaliReceiverPaymentSchema(BaseSchema):
    id: Optional[int] = None
    cheque_number: str
    amount: float
    firm_bank_id: int
    firm_id: int
    received_date: str
    firm_bank_name: Optional[str] = None
    firm_name: Optional[str] = None

    @field_validator("received_date", mode="before")
    @classmethod
    def parse_received_date(cls, v):
        # return in yyyy-mm-dd format
        if isinstance(v, datetime) or isinstance(v, date):
            return v.strftime("%Y-%m-%d")
        return v

class DalaliSenderPaymentSchema(BaseSchema):
    id: Optional[int] = None
    bank_id: int
    cheque_number: str
    cheque_date: Optional[date] = None
    amount: float
    bank_name: Optional[str] = None

class SettlementPaymentSchema(BaseSchema):
    parent_dalali_id: Optional[int] = None
    parent_memo_id: Optional[int] = None
    settlement_type: str
    memo_id: int
    amount: float
    memo_number: int
    id: Optional[int] = None

class PartDalaliSchema(BaseSchema):
    id: Optional[int] = None
    dalali_id: Optional[int] = None
    supplier_id: int
    used: bool
    use_dalali_id: Optional[int] = None
    dalali_number: Optional[int] = None
    dalali_amount: Optional[float] = None

class DalaliBillSchema(BaseSchema):
    id: int
    memo_id: int
    memo_number: Optional[int] = None
    commision: Optional[float] = None
    less_gst_percentage: Optional[float] = None
    less_gst: Optional[float] = None
    register_date: Optional[str] = None
    party_name: Optional[str] = None
    memo_amount: Optional[float] = None
    commission_rate: Optional[float] = None

    @field_validator("register_date", mode="before")
    @classmethod
    def parse_register_date(cls, v):
        # return in yyyy-mm-dd format
        if isinstance(v, datetime) or isinstance(v, date):
            return v.strftime("%d/%m/%Y")
        return v

class LessDetailsSchema(BaseSchema):
    other_details: List[str] = []

class SupplierScehma(BaseSchema):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    email: Optional[str] = None
    pin_code: Optional[str] = None

class InvoiceFirmSchema(BaseSchema):
    id: int
    name: str
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None

class InvoiceFirmBankSchema(BaseSchema):
    id: int
    name: str
    address: Optional[str] = None
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    ifsc: Optional[str] = None
    branch: Optional[str] = None

class DalaliEntrySchema(BaseSchema):
    id: Optional[int] = None
    dalali_number: int
    supplier_id: int
    register_date: str
    amount: float
    deduction: float
    tds_deduction: float
    other_deduction: float
    settlement_deduction: float
    gst_addition: Optional[float] = None
    less_details: Optional[LessDetailsSchema] = None
    notes: Optional[List[str]] = []
    type: str  # "Full" or "Part" (1 or 2)
    status: str  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_no: Optional[str] = None

    # Tax invoice (frozen on save)
    billing_firm_id: Optional[int] = None
    billing_firm_bank_id: Optional[int] = None
    bill_date: Optional[str] = None
    invoice_number: Optional[str] = None
    gst_rate: Optional[float] = None
    place_of_supply: Optional[str] = None
    place_of_supply_name: Optional[str] = None
    taxable_amount: Optional[float] = None
    cgst_amount: Optional[float] = None
    sgst_amount: Optional[float] = None
    igst_amount: Optional[float] = None
    round_off: Optional[float] = None
    grand_total: Optional[float] = None
    grand_total_in_words: Optional[str] = None
    sac_code: Optional[str] = None
    billing_firm: Optional[InvoiceFirmSchema] = None
    billing_firm_bank: Optional[InvoiceFirmBankSchema] = None
    # Set by the API: why it can't be approved yet (None = ready).
    approval_problem: Optional[str] = None
    
    # Relationships
    dalali_bills: List[DalaliBillSchema] = []
    part_dalali: List[PartDalaliSchema] = []
    settlement_payments: List[SettlementPaymentSchema] = []
    dalali_sender_payments: List[DalaliSenderPaymentSchema] = []
    dalali_receiver_payments: List[DalaliReceiverPaymentSchema] = []
    tds_details: List[TdsDetailSchema] = []

    # Other fields
    supplier: Optional[SupplierScehma] = None
    total_part_dalali_amount: Optional[float] = None
    
    created_by: Optional[int] = None
    last_updated_by: Optional[int] = None
    creator: Optional[UserSchema] = None
    last_updater: Optional[UserSchema] = None

    @field_validator("notes", mode="before")
    @classmethod
    def parse_notes_if_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for 'notes'")
        return v
    
    @field_validator("register_date", "bill_date", mode="before")
    @classmethod
    def parse_register_date(cls, v):
        # return in yyyy-mm-dd format
        if isinstance(v, (datetime, date)):
            return v.strftime("%Y-%m-%d")
        return v

# Tax-invoice inputs shared by create and update. gst_rate: 18 / 5 / 0;
# leaving it out keeps the old typed-in gst_addition behaviour.
class DalaliInvoiceInput(BaseSchema):
    billing_firm_id: Optional[int] = None
    billing_firm_bank_id: Optional[int] = None
    bill_date: Optional[date] = None
    invoice_number: Optional[str] = None
    gst_rate: Optional[float] = None
    place_of_supply: Optional[str] = None
    # Part entries only (they have no memos): the commission being billed.
    taxable_amount: Optional[float] = None

    @field_validator("bill_date", mode="before")
    @classmethod
    def parse_bill_date(cls, v):
        if v in ("", None):
            return None
        if isinstance(v, str) and "T" in v:
            return v.split("T")[0]
        return v

    @field_validator("invoice_number", "place_of_supply", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

# Optimized input schemas for related entities
class DalaliBillCreate(BaseSchema):
    memo_id: int

class PartDalaliUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    supplier_id: int
    used: bool = False
    use_dalali_id: Optional[int] = None


class SettlementPaymentCreate(BaseSchema):
    settlement_type: str
    memo_id: int
    amount: float
    memo_number: int
    parent_dalali_id: Optional[int] = None
    parent_memo_id: Optional[int] = None

class DalaliSenderPaymentCreate(BaseSchema):
    bank_id: int
    cheque_number: str
    cheque_date: Optional[date] = None
    amount: int

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        if isinstance(v, str):
            return int(float(v))
        if isinstance(v, float):
            return int(v)
        return v

class DalaliReceiverPaymentCreate(BaseSchema):
    firm_id: int
    firm_bank_id: int
    cheque_number: str
    amount: int
    received_date: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        if isinstance(v, str):
            return int(float(v))
        if isinstance(v, float):
            return int(v)
        return v

class TdsDetailCreate(BaseSchema):
    amount: float
    notes: Optional[str] = None

class DalaliEntryCreate(DalaliInvoiceInput):
    dalali_number: int
    supplier_id: int
    register_date: datetime
    amount: float
    deduction: float
    tds_deduction: float
    other_deduction: float
    settlement_deduction: float
    gst_addition: Optional[float] = 0
    less_details: Optional[Dict[str, List[str]]] = None
    notes: Optional[List[str]] = None
    type: Union[str, int]  # "Full" or "Part" (1 or 2)
    status: Union[str, int]  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_no: Optional[str] = None
    
    # Relationships with specific schemas
    dalali_bills: Optional[List[DalaliBillCreate]] = None
    part_dalali: Optional[List[PartDalaliUpdate]] = None
    settlement_payments: Optional[List[SettlementPaymentCreate]] = None
    dalali_sender_payments: Optional[List[DalaliSenderPaymentCreate]] = None
    dalali_receiver_payments: Optional[List[DalaliReceiverPaymentCreate]] = None
    tds_details: Optional[List[TdsDetailCreate]] = None
    created_by: Optional[int] = None
    
    @field_validator('type')
    def validate_type(cls, v):
        if isinstance(v, int):
            if v == 1:
                return "Full"
            elif v == 2:
                return "Part"
            else:
                raise ValueError("Type must be 1 (Full) or 2 (Part)")
        return v
    
    @field_validator('status')
    def validate_status(cls, v):
        if isinstance(v, int):
            if v == 1:
                return "Pending"
            elif v == 2:
                return "Approved"
            elif v == 3:
                return "Cancelled"
            else:
                raise ValueError("Status must be 1 (Pending), 2 (Approved), or 3 (Cancelled)")
        return v

# Optimized input schemas for update operations
class DalaliBillUpdate(BaseSchema):
    id: Optional[int] = None  # Required for identifying which memo to link
    memo_id: int

class SettlementPaymentUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    settlement_type: str
    memo_id: int
    amount: float
    memo_number: int
    parent_dalali_id: Optional[int] = None
    parent_memo_id: Optional[int] = None

class DalaliSenderPaymentUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    bank_id: int
    cheque_number: str
    amount: float

class DalaliReceiverPaymentUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    firm_id: int
    firm_bank_id: int
    cheque_number: str
    amount: float
    received_date: datetime

class TdsDetailUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    amount: float
    notes: Optional[str] = None
    checked: Optional[bool] = False

class DalaliEntryUpdate(DalaliInvoiceInput):
    dalali_number: Optional[int] = None
    supplier_id: Optional[int] = None
    register_date: Optional[datetime] = None
    amount: Optional[float] = None
    deduction: Optional[float] = None
    tds_deduction: Optional[float] = None
    other_deduction: Optional[float] = None
    settlement_deduction: Optional[float] = None
    gst_addition: Optional[float] = None
    less_details: Optional[Dict[str, List[str]]] = None
    notes: Optional[List[str]] = None
    type: Optional[Union[str, int]] = None  # "Full" or "Part" (1 or 2)
    status: Optional[Union[str, int]] = None  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_no: Optional[str] = None
    
    # Relationships with specific schemas
    dalali_bills: Optional[List[DalaliBillUpdate]] = None
    part_dalali: Optional[List[PartDalaliUpdate]] = None
    settlement_payments: Optional[List[SettlementPaymentUpdate]] = None
    dalali_sender_payments: Optional[List[DalaliSenderPaymentUpdate]] = None
    dalali_receiver_payments: Optional[List[DalaliReceiverPaymentUpdate]] = None
    tds_details: Optional[List[TdsDetailUpdate]] = None
    
    last_updated_by: Optional[int] = None
    
    @field_validator('type')
    def validate_type(cls, v):
        if v is None:
            return v
        if isinstance(v, int):
            if v == 1:
                return "Full"
            elif v == 2:
                return "Part"
            else:
                raise ValueError("Type must be 1 (Full) or 2 (Part)")
        return v
    
    @field_validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        if isinstance(v, int):
            if v == 1:
                return "Pending"
            elif v == 2:
                return "Approved"
            elif v == 3:
                return "Cancelled"
            else:
                raise ValueError("Status must be 1 (Pending), 2 (Approved), or 3 (Cancelled)")
        return v

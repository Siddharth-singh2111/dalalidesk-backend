from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime
from pydantic import Field, field_validator
from .base import BaseSchema
from .user import UserSchema

class TdsDetailSchema(BaseSchema):
    id: Optional[int] = None
    amount: float
    note: Optional[str] = None
    checked: bool
    dalali_id: Optional[int] = None

class DalaliReceiverPaymentSchema(BaseSchema):
    id: Optional[int] = None
    cheque: str
    amount: str
    firm_bank_id: int
    firm_id: int
    received_date: datetime

class DalaliSenderPaymentSchema(BaseSchema):
    id: Optional[int] = None
    bank: str
    bank_id: int
    cheque: str
    amount: str

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

class DalaliBillSchema(BaseSchema):
    id: int
    memo_number: int

class LessDetailsSchema(BaseSchema):
    other_details: List[str] = []

class DalaliEntrySchema(BaseSchema):
    id: Optional[int] = None
    dalali_number: int
    supplier_id: int
    register_date: datetime
    amount: float
    deduction: float
    tds_deduction: float
    other_deduction: float
    settlement_deduction: float
    less_details: Optional[LessDetailsSchema] = None
    notes: List[str] = []
    type: str  # "Full" or "Part" (1 or 2)
    status: str  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_number: Optional[str] = None
    
    # Relationships
    dalali_bills: List[DalaliBillSchema] = []
    part_dalali: List[PartDalaliSchema] = []
    settlement_payments: List[SettlementPaymentSchema] = []
    dalali_sender_payments: List[DalaliSenderPaymentSchema] = []
    dalali_receiver_payments: List[DalaliReceiverPaymentSchema] = []
    tds_details: List[TdsDetailSchema] = []
    
    created_by: Optional[int] = None
    last_updated_by: Optional[int] = None
    creator: Optional[UserSchema] = None
    last_updater: Optional[UserSchema] = None

# Optimized input schemas for related entities
class DalaliBillCreate(BaseSchema):
    memo_id: int

class PartDalaliCreate(BaseSchema):
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
    cheque: str
    amount: str

class DalaliReceiverPaymentCreate(BaseSchema):
    firm_id: int
    firm_bank_id: int
    cheque: str
    amount: str
    received_date: datetime

class TdsDetailCreate(BaseSchema):
    amount: float
    note: Optional[str] = None

class DalaliEntryCreate(BaseSchema):
    dalali_number: int
    supplier_id: int
    register_date: datetime
    amount: float
    deduction: float
    tds_deduction: float
    other_deduction: float
    settlement_deduction: float
    less_details: Optional[Dict[str, List[str]]] = None
    notes: Optional[List[str]] = None
    type: Union[str, int]  # "Full" or "Part" (1 or 2)
    status: Union[str, int]  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_number: Optional[str] = None
    
    # Relationships with specific schemas
    dalali_bills: Optional[List[DalaliBillCreate]] = None
    part_dalali: Optional[List[PartDalaliCreate]] = None
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

class PartDalaliUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    supplier_id: int
    used: bool = False
    use_dalali_id: Optional[int] = None

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
    cheque: str
    amount: str

class DalaliReceiverPaymentUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    firm_id: int
    firm_bank_id: int
    cheque: str
    amount: str
    received_date: datetime

class TdsDetailUpdate(BaseSchema):
    id: Optional[int] = None  # Optional for identifying existing record
    amount: float
    note: Optional[str] = None
    checked: bool = False

class DalaliEntryUpdate(BaseSchema):
    dalali_number: Optional[int] = None
    supplier_id: Optional[int] = None
    register_date: Optional[datetime] = None
    amount: Optional[float] = None
    deduction: Optional[float] = None
    tds_deduction: Optional[float] = None
    other_deduction: Optional[float] = None
    settlement_deduction: Optional[float] = None
    less_details: Optional[Dict[str, List[str]]] = None
    notes: Optional[List[str]] = None
    type: Optional[Union[str, int]] = None  # "Full" or "Part" (1 or 2)
    status: Optional[Union[str, int]] = None  # "Pending", "Approved", "Cancelled" (1, 2, 3)
    reference_page_number: Optional[int] = None
    tally_bill_number: Optional[str] = None
    
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

from typing import List, Optional
from datetime import datetime
from pydantic import Field, field_serializer, field_validator 
from .base import BaseSchema
from .user import UserSchema
class MemoBillSchema(BaseSchema):
    id: int
    memo_id: int
    type: str

class MemoEntrySchema(BaseSchema):
    id: int
    memo_number: int
    amount: int
    register_date: datetime
    created_by: Optional[int] = None
    last_updated_by: Optional[int] = None
    
    # Relationships
    memo_bills: List[MemoBillSchema] = []

    creator: Optional[UserSchema] = None
    last_updater: Optional[UserSchema] = None

     # Field serializer for 'register_date'
    # This function will be called when the model is serialized (e.g., to dict or JSON)
    @field_serializer('register_date')
    def serialize_register_date(self, dt: datetime, _info):
        """
        Serializes the register_date to DD/MM/YYYY format.
        """
        return dt.strftime('%d/%m/%Y')

    # If you also need to parse "DD/MM/YYYY" strings during input (deserialization)
    # while still accepting datetime objects, you can add a validator.
    # This is useful if the input data might come as a pre-formatted string.
    @field_validator('register_date')
    def parse_register_date(cls, value):
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%d/%m/%Y')
            except ValueError:
                # You might want to raise a custom error or let Pydantic handle it
                raise ValueError("register_date must be a valid date in DD/MM/YYYY format or a datetime object")
        if isinstance(value, datetime):
            return value
        raise ValueError("register_date must be a datetime object or a string in DD/MM/YYYY format")
    
class MemoEntryCreate(BaseSchema):
    memo_number: int
    created_by: Optional[int] = None

class MemoEntryUpdate(BaseSchema):
    memo_number: Optional[int] = None
    last_updated_by: Optional[int] = None

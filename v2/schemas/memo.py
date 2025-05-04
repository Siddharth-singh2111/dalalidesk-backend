from typing import List, Optional
from datetime import datetime
from pydantic import Field
from .base import BaseSchema

class MemoBillSchema(BaseSchema):
    id: int
    memo_id: int
    type: str

class MemoEntrySchema(BaseSchema):
    id: int
    memo_number: int
    created_by: Optional[int] = None
    last_updated_by: Optional[int] = None
    
    # Relationships
    memo_bills: List[MemoBillSchema] = []
    
class MemoEntryCreate(BaseSchema):
    memo_number: int
    created_by: Optional[int] = None

class MemoEntryUpdate(BaseSchema):
    memo_number: Optional[int] = None
    last_updated_by: Optional[int] = None

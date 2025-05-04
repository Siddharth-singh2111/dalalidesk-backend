from typing import List, Optional
from datetime import datetime
from pydantic import Field
from .base import BaseSchema

class UserSchema(BaseSchema):
    id: int
    username: str

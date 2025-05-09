from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from datetime import datetime
from typing import Optional, List

class Bank(db.Model):
    __tablename__ = "bank"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    name: Mapped[str] = MappedColumn(db.String(100), nullable=False, unique=True)
    address: Mapped[Optional[str]] = MappedColumn(db.String(300), nullable=True)
    phone_number: Mapped[Optional[str]] = MappedColumn(db.String(20), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)

class Firm(db.Model):
    __tablename__ = "firm"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    name: Mapped[str] = MappedColumn(db.String(100), nullable=False, unique=True)
    address: Mapped[Optional[str]] = MappedColumn(db.String(300), nullable=True)
    phone_number: Mapped[Optional[str]] = MappedColumn(db.String(20), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)



class FirmBank(db.Model):
    __tablename__ = "firm_bank"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    firm_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("firm.id"), nullable=False)
    name: Mapped[str] = MappedColumn(db.String(100), nullable=False)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
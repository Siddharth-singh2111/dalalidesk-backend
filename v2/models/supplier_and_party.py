from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy import CheckConstraint
from datetime import datetime
from typing import Optional, List


ALLOWED_CITIES = ['Bangalore', 'Jaipur', 'Kolkata', 'Surat', 'Varanasi', 'Belgaum', 'Mumbai', 'Delhi', 'Mau']

class Supplier(db.Model):
    __tablename__ = "supplier"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    name: Mapped[str] = MappedColumn(db.String(100), nullable=False, unique=True)
    address: Mapped[Optional[str]] = MappedColumn(db.String(300), nullable=True)
    phone_number: Mapped[Optional[str]] = MappedColumn(db.String(20), nullable=True)
    city: Mapped[Optional[str]] = MappedColumn(db.String(20), nullable=True)
    gst_default: Mapped[Optional[float]] = MappedColumn(db.Numeric, default=5.0, nullable=True)
    last_update: Mapped[datetime] = MappedColumn(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    dalali_entries = relationship("DalaliEntry", back_populates="supplier")
    memo_entries = relationship("MemoEntry", back_populates="supplier")
    # User relationships for audit
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    # CHECK constraint for city
    city_string = ', '.join([f"'{city}'" for city in ALLOWED_CITIES])
    __table_args__ = (
        CheckConstraint(f"city IN ({city_string})", name="check_supplier_city"),
    )


class Party(db.Model):
    __tablename__ = "party"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    name: Mapped[str] = MappedColumn(db.String(100), nullable=False, unique=True)

    memo_entries = relationship("MemoEntry", back_populates="party")
    

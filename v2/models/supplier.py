from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from datetime import datetime
from typing import Optional, List


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
    __table_args__ = (
        db.CheckConstraint("city IN ('Bangalore', 'Jaipur', 'Kolkata', 'Surat', 'Varanasi', 'Belgaum', 'Mumbai', 'Delhi', 'Mau')", name="check_supplier_city"),
    )

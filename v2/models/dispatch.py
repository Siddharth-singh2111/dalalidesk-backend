"""
Dispatch models — digitises the physical "Dispatch Pad" (G. Das & Company /
D.M. Agency). A dispatch is a batch of bills handed to a single local party on a
given day, each bill carrying its own L.R. No. and transport name.

    dispatch        -> one pad slip (party + date + serial), by a user
    dispatch_bill   -> one printed row on the slip (a bill + L.R. No. + transport)
"""
from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, date
from typing import Optional, List


class Dispatch(db.Model):
    __tablename__ = "dispatch"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    # The pre-printed serial number on the pad (e.g. 484). Optional.
    serial_number: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    party_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("party.id"), nullable=False)
    dispatch_date: Mapped[date] = MappedColumn(db.Date, default=date.today, nullable=False)
    notes: Mapped[Optional[str]] = MappedColumn(db.String(300), nullable=True)

    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    party = relationship("Party")
    bills = relationship(
        "DispatchBill",
        back_populates="dispatch",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    creator = relationship("Users", foreign_keys=[created_by])
    last_updater = relationship("Users", foreign_keys=[last_updated_by])

    @hybrid_property
    def bill_count(self) -> int:
        """Number of bills on this dispatch slip."""
        return len(self.bills)


class DispatchBill(db.Model):
    __tablename__ = "dispatch_bill"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dispatch_id: Mapped[int] = MappedColumn(
        db.Integer, db.ForeignKey("dispatch.id", ondelete="CASCADE"), nullable=False
    )
    # Best-effort link to the underlying register entry (may be null if the bill
    # can't be resolved). The denormalised fields below always carry the values.
    register_entry_id: Mapped[Optional[int]] = MappedColumn(
        db.Integer, db.ForeignKey("register_entry.id"), nullable=True
    )
    bill_number: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    bill_date: Mapped[Optional[date]] = MappedColumn(db.Date, nullable=True)
    supplier_id: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=True)
    lr_number: Mapped[Optional[str]] = MappedColumn(db.String(50), nullable=True)
    transport_name: Mapped[Optional[str]] = MappedColumn(db.String(100), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    dispatch = relationship("Dispatch", back_populates="bills")
    supplier = relationship("Supplier")
    register_entry = relationship("RegisterEntry")

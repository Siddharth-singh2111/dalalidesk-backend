from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from .supplier import Supplier
from .firms_and_banks import Bank, Firm, FirmBank


# -- dalali_entry
# CREATE TABLE dalali_entry (
#   id SERIAL PRIMARY KEY,
#   dalali_number INTEGER NOT NULL,
#   supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
#   register_date DATE,
#   amount NUMERIC,
#   deduction NUMERIC,
#   tds_deduction NUMERIC,
#   other_deduction NUMERIC,
#   settlement_deduction NUMERIC
#   other_details TEXT,
#   notes TEXT,
#   type VARCHAR(10) NOT NULL CHECK (type IN ('Full','Part')),
#   status VARCHAR(10) NOT NULL CHECK (status IN ('Approved','Pending','Cancelled')),
#   reference_page_number INTEGER,
#   tally_bill_no VARCHAR(50),
# );

class DalaliEntry(db.Model):
    __tablename__ = "dalali_entry"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_number: Mapped[int] = MappedColumn(db.Integer, nullable=False, unique=True)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    register_date: Mapped[datetime] = MappedColumn(db.DateTime, nullable=False)
    amount: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    deduction: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    tds_deduction: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    other_deduction: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    settlement_deduction: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    other_details: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    notes: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    type: Mapped[str] = MappedColumn(db.String(10), nullable=False)
    status: Mapped[str] = MappedColumn(db.String(10), nullable=False)
    reference_page_number: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    tally_bill_no: Mapped[Optional[str]] = MappedColumn(db.String(50), nullable=True)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="dalali_entries")
    dalali_bills = relationship("DalaliBills", back_populates="dalali_entry", cascade="all, delete-orphan")
    # This represents other dalali entries that were used by this dalali entry
    part_dalali = relationship("PartDalali", foreign_keys="PartDalali.use_dalali_id", back_populates="use_dalali", cascade="all, delete-orphan")
    dalali_sender_payments = relationship("DalaliSenderPayments", back_populates="dalali_entry", cascade="all, delete-orphan")
    dalali_receiver_payments = relationship("DalaliReceiverPayments", back_populates="dalali_entry", cascade="all, delete-orphan")
    tds_details = relationship("TdsDetails", back_populates="dalali_entry", cascade="all, delete-orphan")
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    # Hybrid properties for formatted data access
    @hybrid_property
    def less_details(self) -> Dict[str, List[Any]]:
        """
        Format other_details as a dict with the structure:
        {
            "other_details": [...]
        }
        """
        if self.other_details:
            try:
                other_details_list = json.loads(self.other_details)
            except json.JSONDecodeError:
                other_details_list = [self.other_details]
            return {"other_details": other_details_list}
        return {"other_details": []}

    # Check constraint for type and status
    __table_args__ = (
        db.CheckConstraint("type IN ('Full', 'Part')", name="check_dalali_type"),
        db.CheckConstraint("status IN ('Approved', 'Pending', 'Cancelled')", name="check_dalali_status"),
        db.UniqueConstraint('dalali_number', name='uq_dalali_number'),
    )


# -- dalali_bills
# CREATE TABLE dalali_bills (
#   id SERIAL PRIMARY KEY,
#   dalali_id INTEGER NOT NULL REFERENCES dalali_entry(id) ON DELETE CASCADE,
#   memo_id INTEGER NOT NULL REFERENCES memo_entry(id)
# );

class DalaliBills(db.Model):
    __tablename__ = "dalali_bills"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id", ondelete="CASCADE"), nullable=False)
    memo_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    dalali_entry = relationship("DalaliEntry", back_populates="dalali_bills")
    memo_entry = relationship("MemoEntry", back_populates="dalali_bills")

    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    @hybrid_property
    def memo_number(self) -> Optional[int]:
        """
        Return the memo number from the related MemoEntry.
        """
        if self.memo_entry:
            return self.memo_entry.memo_number
        return None
    
    @hybrid_property
    def commision(self) -> Optional[float]:
        """
        Return the amount from the related MemoEntry.
        """
        if self.memo_entry:
            return self.memo_entry.commision
        return None
    
    @hybrid_property
    def less_gst_percent(self) -> Optional[float]:
        """
        Return the less_gst_percent from the related MemoEntry.
        """
        if self.memo_entry:
            return self.memo_entry.less_gst_percentage
        return None
    
    @hybrid_property
    def register_date(self) -> Optional[datetime]:
        """
        Return the register_date from the related MemoEntry.
        """
        if self.memo_entry:
            return self.memo_entry.register_date
        return None


# -- part_dalali
# CREATE TABLE part_dalali (
#   id SERIAL PRIMARY KEY,
#   dalali_id INTEGER NOT NULL REFERENCES dalali_entry(id) ON DELETE CASCADE,
#   supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
#   used BOOLEAN NOT NULL DEFAULT FALSE
#   use_dalali_id INTEGER REFERENCES dalali_entry(id)
# );

class PartDalali(db.Model):
    __tablename__ = "part_dalali"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    used: Mapped[bool] = MappedColumn(db.Boolean, nullable=False, default=False)
    use_dalali_id: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id"), nullable=True)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    # dalali_entry is the original dalali entry that might be used by another dalali
    dalali_entry = relationship("DalaliEntry", foreign_keys=[dalali_id])
    # use_dalali is the dalali entry that uses this part dalali
    use_dalali = relationship("DalaliEntry", foreign_keys=[use_dalali_id], back_populates="part_dalali")
    supplier = relationship("Supplier")
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    @hybrid_property
    def dalali_number(self) -> Optional[int]:
        """
        Return the dalali number from the related DalaliEntry.
        """
        if self.dalali_entry:
            return self.dalali_entry.dalali_number
        return None
    @hybrid_property
    def dalali_amount(self) -> Optional[float]:
        """
        Return the dalali amount from the related DalaliEntry.
        """
        if self.dalali_entry:
            return self.dalali_entry.amount
        return None


# -- dalali_sender_payments
# CREATE TABLE dalali_sender_payments (
#   id SERIAL PRIMARY KEY,
#   dalali_id INTEGER NOT NULL REFERENCES dalali_entry(id) ON DELETE CASCADE,
#   bank_id INTEGER NOT NULL REFERENCES bank(id),
#   amount NUMERIC
#   cheque_number VARCHAR(50)
# );

class DalaliSenderPayments(db.Model):
    __tablename__ = "dalali_sender_payments"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id", ondelete="CASCADE"), nullable=False)
    bank_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("bank.id"), nullable=False)
    amount: Mapped[Optional[float]] = MappedColumn(db.Numeric, nullable=True)
    cheque_number: Mapped[Optional[str]] = MappedColumn(db.String(50), nullable=True)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    dalali_entry = relationship("DalaliEntry", back_populates="dalali_sender_payments")
    bank = relationship("Bank", foreign_keys=[bank_id])
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    @hybrid_property
    def bank_name(self) -> Optional[str]:
        """
        Return the bank name from the related Bank.
        """
        if self.bank:
            return self.bank.name
        return None


# -- dalali_receiver_payments
# CREATE TABLE dalali_receiver_payments (
#   id SERIAL PRIMARY KEY,
#   dalali_id INTEGER NOT NULL REFERENCES dalali_entry(id) ON DELETE CASCADE,
#   firm_id INTEGER NOT NULL REFERENCES firm(id),   
#   firm_bank_id INTEGER NOT NULL REFERENCES firm_bank(id),
#   amount NUMERIC
#   received_date DATE
#   cheque_number VARCHAR(50)
# );

class DalaliReceiverPayments(db.Model):
    __tablename__ = "dalali_receiver_payments"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id", ondelete="CASCADE"), nullable=False)
    firm_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("firm.id"), nullable=False)
    firm_bank_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("firm_bank.id"), nullable=False)
    amount: Mapped[Optional[float]] = MappedColumn(db.Numeric, nullable=True)
    received_date: Mapped[Optional[datetime]] = MappedColumn(db.Date, nullable=True)
    cheque_number: Mapped[Optional[str]] = MappedColumn(db.String(50), nullable=True)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    dalali_entry = relationship("DalaliEntry", back_populates="dalali_receiver_payments")
    firm = relationship("Firm", foreign_keys=[firm_id])
    firm_bank = relationship("FirmBank", foreign_keys=[firm_bank_id])

    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    @hybrid_property
    def firm_name(self) -> Optional[str]:
        """
        Return the firm name from the related Firm.
        """
        if self.firm:
            return self.firm.name
        return None
    
    @hybrid_property
    def firm_bank_name(self) -> Optional[str]:
        """
        Return the firm bank name from the related FirmBank.
        """
        if self.firm_bank:
            return self.firm_bank.name
        return None


# -- tds_details
# CREATE TABLE tds_details (
#   id SERIAL PRIMARY KEY,
#   dalali_id INTEGER NOT NULL REFERENCES dalali_entry(id) ON DELETE CASCADE,
#   amount NUMERIC
#   notes TEXT
#   checked boolean
# );

class TdsDetails(db.Model):
    __tablename__ = "tds_details"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    dalali_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("dalali_entry.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Optional[float]] = MappedColumn(db.Numeric, nullable=True)
    notes: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    checked: Mapped[Optional[bool]] = MappedColumn(db.Boolean, nullable=True)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    dalali_entry = relationship("DalaliEntry", back_populates="tds_details")
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

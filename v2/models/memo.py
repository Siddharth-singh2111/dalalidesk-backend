from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
from .supplier_and_party import Supplier, Party
from .firms_and_banks import Bank


# -- memo_entry
# CREATE TABLE memo_entry(
#     id INT DEFAULT NEXTVAL ('memo_entry_seq') PRIMARY KEY,
#     memo_number INT,
#     supplier_id INT,
#     party_id INT, 
#     register_date TIMESTAMP(0),
#     amount INT default 0,
#     gr_amount INT default 0,
#     deduction INT default 0,
#     discount INT DEFAULT 0,
#     other_deduction INT DEFAULT 0,
#     rate_difference INT DEFAULT 0,
#     gr_amount_details TEXT,
#     discount_details TEXT,
#     other_deduction_details TEXT,
#     rate_difference_details TEXT,
#     notes TEXT,
#     parent_dalali_id INT,
#     parent_memo_id INT,
#     memo_type VARCHAR(20) CHECK (memo_type IN ('Full', 'Part', 'Payment Settlement', 'Dalali Settlement')) DEFAULT 'Full',
#     less_gst_percentage DECIMAL,
#     less_gst INT DEFAULT 0,
#     commision INT DEFAULT 0,
# );

class MemoEntry(db.Model):
    __tablename__ = "memo_entry"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    memo_number: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    party_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("party.id"), nullable=False)
    register_date: Mapped[datetime] = MappedColumn(db.DateTime, default=datetime.now, nullable=False)
    amount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    gr_amount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    deduction: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    discount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    other_deduction: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    rate_difference: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    gr_amount_details: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    discount_details: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    other_deduction_details: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    rate_difference_details: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    notes: Mapped[Optional[str]] = MappedColumn(db.Text, nullable=True)
    parent_dalali_id: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    parent_memo_id: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=True)
    memo_type: Mapped[str] = MappedColumn(db.String(20), default="Full", nullable=False)
    less_gst_percentage: Mapped[Optional[float]] = MappedColumn(db.Numeric, nullable=True)
    less_gst: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    commision: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="memo_entries")
    party = relationship("Party", back_populates="memo_entries")
    
    # Self-referential relationship for parent/child memos
    child_memos = relationship("MemoEntry", 
                               backref=db.backref('parent_memo', remote_side=[id]))
    
    # Related objects
    memo_bills = relationship(
        "MemoBills",
        back_populates="memo_entry",
        lazy="selectin",
    )
    
    memo_payments = relationship(
        "MemoPayments",
        back_populates="memo_entry",
        lazy="selectin",
    )
    
    dalali_bills = relationship(
        "DalaliBills",
        back_populates="memo_entry",
        lazy="selectin"
    )
    
    # This represents part payments that originated from this memo
    part_payments_source = relationship(
        "PartPayments",
        foreign_keys="PartPayments.memo_id",
        back_populates="memo_entry",
        lazy="selectin"
    )
    
    # This represents part payments that were used by this memo
    part_payments_used = relationship(
        "PartPayments",
        foreign_keys="PartPayments.use_memo_id",
        back_populates="use_memo",
        lazy="selectin"
    )
    
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

    # Hybrid properties
    @hybrid_property
    def total_bill_amount(self) -> int:
        """
        Return the total bill amount from all memo bills.
        """
        return sum(bill.amount for bill in self.memo_bills if bill.amount)
    
    @hybrid_property
    def total_payment_amount(self) -> int:
        """
        Return the total payment amount from all memo payments.
        """
        return sum(payment.amount for payment in self.memo_payments if payment.amount)
    
    @hybrid_property
    def net_amount(self) -> int:
        """
        Calculate the net amount after all deductions.
        """
        return (self.amount - self.gr_amount - self.deduction - self.discount - 
                self.other_deduction - self.rate_difference - self.less_gst)
    
    @hybrid_property
    def formatted_gr_details(self) -> Dict[str, List[Any]]:
        """
        Format gr_amount_details as a dict with the structure:
        {
            "gr_details": [...]
        }
        """
        if self.gr_amount_details:
            try:
                gr_details_list = json.loads(self.gr_amount_details)
            except json.JSONDecodeError:
                gr_details_list = [self.gr_amount_details]
            return {"gr_details": gr_details_list}
        return {"gr_details": []}
    
    @hybrid_property
    def formatted_discount_details(self) -> Dict[str, List[Any]]:
        """
        Format discount_details as a dict with the structure:
        {
            "discount_details": [...]
        }
        """
        if self.discount_details:
            try:
                discount_details_list = json.loads(self.discount_details)
            except json.JSONDecodeError:
                discount_details_list = [self.discount_details]
            return {"discount_details": discount_details_list}
        return {"discount_details": []}
    
    @hybrid_property
    def formatted_other_deduction_details(self) -> Dict[str, List[Any]]:
        """
        Format other_deduction_details as a dict with the structure:
        {
            "other_deduction_details": [...]
        }
        """
        if self.other_deduction_details:
            try:
                other_deduction_details_list = json.loads(self.other_deduction_details)
            except json.JSONDecodeError:
                other_deduction_details_list = [self.other_deduction_details]
            return {"other_deduction_details": other_deduction_details_list}
        return {"other_deduction_details": []}
    
    @hybrid_property
    def formatted_rate_difference_details(self) -> Dict[str, List[Any]]:
        """
        Format rate_difference_details as a dict with the structure:
        {
            "rate_difference_details": [...]
        }
        """
        if self.rate_difference_details:
            try:
                rate_difference_details_list = json.loads(self.rate_difference_details)
            except json.JSONDecodeError:
                rate_difference_details_list = [self.rate_difference_details]
            return {"rate_difference_details": rate_difference_details_list}
        return {"rate_difference_details": []}
    
    # Check constraint for memo_type
    __table_args__ = (
        db.CheckConstraint("memo_type IN ('Full', 'Part', 'Payment Settlement', 'Dalali Settlement')", name="check_memo_type"),
        db.UniqueConstraint('memo_number', 'party_id', 'supplier_id', 'register_date', name='unique_memo_entry'),
    )


# -- memo_bills
# CREATE TABLE memo_bills (
#     id INT DEFAULT NEXTVAL ('memo_bills_seq') PRIMARY KEY,
#     memo_id INT, 
#     bill_id INT,
#     type VARCHAR(2),
#     amount INT,
# );

class MemoBills(db.Model):
    __tablename__ = "memo_bills"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    memo_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=False)
    bill_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("register_entry.id"), nullable=False)
    type: Mapped[str] = MappedColumn(db.String(2), nullable=False)
    amount: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    memo_entry = relationship("MemoEntry", back_populates="memo_bills")
    register_entry = relationship("RegisterEntry")
    
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )
    
    @hybrid_property
    def bill_number(self) -> Optional[int]:
        """
        Return the bill number from the related RegisterEntry.
        """
        if self.register_entry:
            return self.register_entry.bill_number
        return None


# -- memo_payments
# CREATE TABLE memo_payments(
#     id INT DEFAULT NEXTVAL ('memo_payments_seq') PRIMARY KEY,
#     memo_id INT, 
#     bank_id INT,
#     cheque_number INT,
#     amount INT DEFAULT 0,
# );

class MemoPayments(db.Model):
    __tablename__ = "memo_payments"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    memo_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=False)
    bank_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("bank.id"), nullable=False)
    cheque_number: Mapped[Optional[int]] = MappedColumn(db.Integer, nullable=True)
    amount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    memo_entry = relationship("MemoEntry", back_populates="memo_payments")
    bank = relationship("Bank")
    
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


# -- part_payments
# CREATE TABLE part_payments(
#     id INT DEFAULT nextval('part_payment_seq') PRIMARY KEY,
#     supplier_id INT,
#     party_id INT,
#     memo_id INT,
#     used boolean DEFAULT false,
#     use_memo_id INT,
# );

class PartPayments(db.Model):
    __tablename__ = "part_payments"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    party_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("party.id"), nullable=False)
    memo_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=False)
    used: Mapped[bool] = MappedColumn(db.Boolean, default=False, nullable=False)
    use_memo_id: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("memo_entry.id"), nullable=True)
    
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    supplier = relationship("Supplier")
    party = relationship("Party")
    memo_entry = relationship("MemoEntry", foreign_keys=[memo_id], back_populates="part_payments_source")
    use_memo = relationship("MemoEntry", foreign_keys=[use_memo_id], back_populates="part_payments_used")
    
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
    def memo_amount(self) -> Optional[int]:
        """
        Return the amount from the related MemoEntry.
        """
        if self.memo_entry:
            return self.memo_entry.amount
        return None
    
    @hybrid_property
    def use_memo_number(self) -> Optional[int]:
        """
        Return the memo number from the use MemoEntry.
        """
        if self.use_memo:
            return self.use_memo.memo_number
        return None

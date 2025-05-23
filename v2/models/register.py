from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from typing import Optional, List
from .supplier_and_party import Supplier, Party


# -- register_entry
# CREATE TABLE register_entry (
#     id INT DEFAULT NEXTVAL ('register_entry_seq') PRIMARY KEY,
#     supplier_id INT,
#     party_id INT, 
#     register_date TIMESTAMP(0),
#     amount INT,
#     bill_number INT,
#     gr_amount INT DEFAULT 0,
#     deduction INT DEFAULT 0,
#     status VARCHAR(2) DEFAULT 'N',
#     partial_amount INT DEFAULT 0,
#     UNIQUE (bill_number, supplier_id, party_id, register_date),
# );

class RegisterEntry(db.Model):
    __tablename__ = "register_entry"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    party_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("party.id"), nullable=False)
    register_date: Mapped[datetime] = MappedColumn(db.DateTime, default=datetime.now, nullable=False)
    amount: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    bill_number: Mapped[int] = MappedColumn(db.Integer, nullable=False)
    gr_amount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    deduction: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    status: Mapped[str] = MappedColumn(db.String(2), default="N", nullable=False)
    partial_amount: Mapped[int] = MappedColumn(db.Integer, default=0, nullable=False)
    
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)

    # Relationships
    supplier = relationship("Supplier")
    party = relationship("Party")
    
    
    memo_bills = relationship(
        "MemoBills",
        back_populates="register_entry",
        lazy="selectin",
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
    def net_amount(self) -> int:
        """
        Calculate the net amount after gr_amount and deduction.
        """
        return self.amount - self.gr_amount - self.deduction
    
    @hybrid_property
    def remaining_amount(self) -> int:
        """
        Calculate the remaining amount after partial payments.
        """
        return self.net_amount - self.partial_amount
    
    @hybrid_property
    def is_settled(self) -> bool:
        """
        Check if the register entry is fully settled.
        """
        return self.status == "Y"
    
    @hybrid_property
    def is_partially_settled(self) -> bool:
        """
        Check if the register entry is partially settled.
        """
        return self.partial_amount > 0 and self.partial_amount < self.net_amount
    
    # Table constraints
    __table_args__ = (
        db.UniqueConstraint('bill_number', 'supplier_id', 'party_id', 'register_date', name='unique_register_entry'),
    )

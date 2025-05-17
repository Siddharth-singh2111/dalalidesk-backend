from ..extensions import db
from datetime import datetime
from .dalali import DalaliBills

class MemoEntry(db.Model):
    __tablename__ = "memo_entry"

    id = db.Column(db.Integer, primary_key=True)
    memo_number = db.Column(db.Integer, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    party_id = db.Column(db.Integer, db.ForeignKey("party.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    register_date = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    commision = db.Column(db.Integer, nullable=True)
    less_gst_percentage = db.Column(db.Integer, nullable=True)
    less_gst = db.Column(db.Integer, nullable=True)

    # Relationships with cascade delete to related objects
    memo_bills = db.relationship(
        "MemoBills",
        back_populates="memo_entry",
        lazy="selectin",
        cascade="all, delete-orphan"  # This ensures cascade delete
    )

    dalali_bills = db.relationship(
        "DalaliBills",
        back_populates="memo_entry",
        lazy="selectin",
    )

    supplier = db.relationship(
        "Supplier",
        back_populates="memo_entries",
    )

    party = db.relationship(
        "Party",
        back_populates="memo_entries",
    )

    creator = db.relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = db.relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )

class MemoBills(db.Model):
    __tablename__ = "memo_bills"

    id = db.Column(db.Integer, primary_key=True)
    memo_id = db.Column(db.Integer, db.ForeignKey("memo_entry.id", ondelete="CASCADE"))
    type = db.Column(db.String)

    memo_entry = db.relationship(
        "MemoEntry",
        back_populates="memo_bills",
    )

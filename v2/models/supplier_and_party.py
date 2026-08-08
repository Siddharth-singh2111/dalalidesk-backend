from ..extensions import db
from sqlalchemy.orm import MappedColumn, Mapped, relationship
from sqlalchemy import CheckConstraint
from datetime import datetime
from typing import Optional, List


# Keep in sync with: the supplier_city_check DB constraint (migrations/expand_supplier_cities.sql
# + API_Database/holani_cloth_agency.sql) and hca_frontend_v2/src/types/entities.ts CITIES.
ALLOWED_CITIES = [
    'Agra', 'Ahmedabad', 'Ajmer', 'Aligarh', 'Amritsar', 'Aurangabad', 'Balotra',
    'Bangalore', 'Bareilly', 'Belgaum', 'Bhagalpur', 'Bhilwara', 'Bhiwandi', 'Bhopal',
    'Burhanpur', 'Chandigarh', 'Chennai', 'Coimbatore', 'Dehradun', 'Delhi', 'Dhanbad',
    'Erode', 'Faridabad', 'Ghaziabad', 'Gorakhpur', 'Gurugram', 'Guwahati', 'Gwalior',
    'Hyderabad', 'Ichalkaranji', 'Indore', 'Jabalpur', 'Jaipur', 'Jalandhar', 'Jamnagar',
    'Jodhpur', 'Kannauj', 'Kanpur', 'Karur', 'Kishangarh', 'Kochi', 'Kolkata', 'Kota',
    'Lucknow', 'Ludhiana', 'Madurai', 'Malegaon', 'Mathura', 'Mau', 'Meerut', 'Moradabad',
    'Mumbai', 'Mysore', 'Nagpur', 'Nashik', 'Noida', 'Pali', 'Panipat', 'Patna', 'Pune',
    'Raipur', 'Rajkot', 'Ranchi', 'Salem', 'Solapur', 'Sonipat', 'Srinagar', 'Surat',
    'Thane', 'Tiruppur', 'Udaipur', 'Ujjain', 'Vadodara', 'Varanasi', 'Vijayawada',
    'Visakhapatnam',
]

class CommissionRate(db.Model):
    """Per supplier+party commission override; absence of a row means the 2% default."""
    __tablename__ = "commission_rates"

    id: Mapped[int] = MappedColumn(db.Integer, primary_key=True)
    supplier_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    party_id: Mapped[int] = MappedColumn(db.Integer, db.ForeignKey("party.id"), nullable=False)
    rate_percent: Mapped[float] = MappedColumn(db.Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)

    __table_args__ = (db.UniqueConstraint("supplier_id", "party_id", name="commission_rates_supplier_party_key"),)


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
    part_payments = relationship("PartPayments", back_populates="supplier")
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
    address: Mapped[Optional[str]] = MappedColumn(db.String(300), nullable=True)
    phone_number: Mapped[Optional[str]] = MappedColumn(db.String(20), nullable=True)
    last_update: Mapped[datetime] = MappedColumn(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)
    created_at: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    created_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = MappedColumn(db.TIMESTAMP(timezone=True), server_default=db.func.current_timestamp(), nullable=False)
    last_updated_by: Mapped[Optional[int]] = MappedColumn(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relationships
    memo_entries = relationship("MemoEntry", back_populates="party")
    part_payments = relationship("PartPayments", back_populates="party")
    
    # User relationships for audit
    creator = relationship(
        "Users",
        foreign_keys=[created_by],
    )
    last_updater = relationship(
        "Users",
        foreign_keys=[last_updated_by],
    )
    

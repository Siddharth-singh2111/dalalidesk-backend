"""
Service layer for Dispatch (digitised Dispatch Pad).

Handles creating a dispatch with its bill rows in a single transaction,
listing/filtering dispatches, fetching one, and deleting.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date

from sqlalchemy import func

from ..extensions import db
from ..models.dispatch import Dispatch, DispatchBill
from ..models.register import RegisterEntry
from ..models.supplier_and_party import Supplier, Party
from ..models.user import Users


def _parse_date(value) -> Optional[date]:
    """Accepts YYYY-MM-DD or DD/MM/YYYY (or a date/datetime) and returns a date."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def _resolve_register_entry_id(bill_number, supplier_id, party_id) -> Optional[int]:
    """Best-effort link to an existing register entry for this bill."""
    if not bill_number or not supplier_id or not party_id:
        return None
    row = (
        db.session.query(RegisterEntry.id)
        .filter(
            RegisterEntry.bill_number == int(bill_number),
            RegisterEntry.supplier_id == int(supplier_id),
            RegisterEntry.party_id == int(party_id),
        )
        .first()
    )
    return row[0] if row else None


class DispatchService:
    @staticmethod
    def create_dispatch(data: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        Create a dispatch and its bills. `data`:
            party_id (int, required)
            dispatch_date (str, required)
            serial_number (int, optional)
            notes (str, optional)
            created_by (int, optional)
            bills: [ { bill_number, bill_date, supplier_id, lr_number, transport_name } ]
        Returns (ok, message, dispatch_id).
        """
        party_id = data.get("party_id")
        dispatch_date = _parse_date(data.get("dispatch_date"))
        bills = data.get("bills") or []

        if not party_id:
            return False, "party_id is required", None
        if dispatch_date is None:
            return False, "dispatch_date is required (YYYY-MM-DD)", None
        if not bills:
            return False, "At least one bill is required", None

        try:
            dispatch = Dispatch(
                party_id=int(party_id),
                dispatch_date=dispatch_date,
                serial_number=int(data["serial_number"]) if data.get("serial_number") not in (None, "") else None,
                notes=data.get("notes") or None,
                created_by=data.get("created_by"),
                last_updated_by=data.get("created_by"),
            )
            db.session.add(dispatch)
            db.session.flush()  # get dispatch.id

            for b in bills:
                supplier_id = b.get("supplier_id")
                bill_number = b.get("bill_number")
                db.session.add(DispatchBill(
                    dispatch_id=dispatch.id,
                    register_entry_id=_resolve_register_entry_id(bill_number, supplier_id, party_id),
                    bill_number=int(bill_number) if bill_number not in (None, "") else None,
                    bill_date=_parse_date(b.get("bill_date")),
                    supplier_id=int(supplier_id) if supplier_id not in (None, "") else None,
                    lr_number=(b.get("lr_number") or None),
                    transport_name=(b.get("transport_name") or None),
                ))

            db.session.commit()
            return True, "Dispatch created", dispatch.id
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to create dispatch: {e}", None

    @staticmethod
    def _serialize(dispatch: Dispatch) -> Dict:
        return {
            "id": dispatch.id,
            "serial_number": dispatch.serial_number,
            "party_id": dispatch.party_id,
            "party_name": dispatch.party.name if dispatch.party else None,
            "dispatch_date": dispatch.dispatch_date.strftime("%Y-%m-%d") if dispatch.dispatch_date else None,
            "notes": dispatch.notes,
            "created_by": dispatch.created_by,
            "user_name": dispatch.creator.full_name if dispatch.creator else None,
            "bill_count": dispatch.bill_count,
            "bills": [
                {
                    "id": b.id,
                    "register_entry_id": b.register_entry_id,
                    "bill_number": b.bill_number,
                    "bill_date": b.bill_date.strftime("%Y-%m-%d") if b.bill_date else None,
                    "supplier_id": b.supplier_id,
                    "supplier_name": b.supplier.name if b.supplier else None,
                    "lr_number": b.lr_number,
                    "transport_name": b.transport_name,
                }
                for b in dispatch.bills
            ],
        }

    @staticmethod
    def get_dispatch(dispatch_id: int) -> Optional[Dict]:
        dispatch = db.session.get(Dispatch, dispatch_id)
        return DispatchService._serialize(dispatch) if dispatch else None

    @staticmethod
    def list_dispatches(party_id: Optional[int] = None,
                        from_date: Optional[str] = None,
                        to_date: Optional[str] = None,
                        limit: int = 200) -> List[Dict]:
        q = db.session.query(Dispatch)
        if party_id:
            q = q.filter(Dispatch.party_id == int(party_id))
        fd = _parse_date(from_date)
        td = _parse_date(to_date)
        if fd:
            q = q.filter(Dispatch.dispatch_date >= fd)
        if td:
            q = q.filter(Dispatch.dispatch_date <= td)
        q = q.order_by(Dispatch.dispatch_date.desc(), Dispatch.id.desc()).limit(limit)
        return [DispatchService._serialize(d) for d in q.all()]

    @staticmethod
    def delete_dispatch(dispatch_id: int) -> Tuple[bool, str]:
        dispatch = db.session.get(Dispatch, dispatch_id)
        if not dispatch:
            return False, "Dispatch not found"
        try:
            db.session.delete(dispatch)
            db.session.commit()
            return True, "Dispatch deleted"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete dispatch: {e}"

    @staticmethod
    def available_bills(party_id: int, day: Optional[str] = None,
                        from_date: Optional[str] = None, to_date: Optional[str] = None,
                        limit: int = 500) -> List[Dict]:
        """
        Register-entry bills for a party, to pull into a dispatch. Optionally
        restricted to a single bill day, or a bill-date range.
        """
        q = (
            db.session.query(RegisterEntry, Supplier.name)
            .outerjoin(Supplier, RegisterEntry.supplier_id == Supplier.id)
            .filter(RegisterEntry.party_id == int(party_id))
        )
        single = _parse_date(day)
        if single:
            q = q.filter(func.date(RegisterEntry.register_date) == single)
        else:
            fd = _parse_date(from_date)
            td = _parse_date(to_date)
            if fd:
                q = q.filter(func.date(RegisterEntry.register_date) >= fd)
            if td:
                q = q.filter(func.date(RegisterEntry.register_date) <= td)
        q = q.order_by(RegisterEntry.register_date, RegisterEntry.bill_number).limit(limit)
        return [
            {
                "register_entry_id": re.id,
                "bill_number": re.bill_number,
                "bill_date": re.register_date.strftime("%Y-%m-%d") if re.register_date else None,
                "supplier_id": re.supplier_id,
                "supplier_name": sname,
                "amount": re.amount,
            }
            for re, sname in q.all()
        ]

    @staticmethod
    def distinct_transports() -> List[str]:
        """Distinct transport names seen so far, for the entry autocomplete + report filter."""
        rows = (
            db.session.query(DispatchBill.transport_name)
            .filter(DispatchBill.transport_name.isnot(None))
            .distinct()
            .order_by(DispatchBill.transport_name)
            .all()
        )
        return [r[0] for r in rows if r[0]]

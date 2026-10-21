from typing import List, Optional, Tuple, Dict, Any, Union, cast
import json
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from hca_backend.Exceptions import DataError
from ..models.dalali import (
    DalaliEntry, DalaliBills, PartDalali, 
    DalaliSenderPayments, DalaliReceiverPayments, TdsDetails
)
from ..models.memo import MemoEntry
from ..models.supplier_and_party import Supplier
from ..models.firms_and_banks import Firm, FirmBank
from ..extensions import db
from . import gst_invoice


def _fmt_inr(value) -> str:
    """12345.5 -> '₹12,345.50' (Indian grouping)."""
    v = gst_invoice.money(value)
    sign = "-" if v < 0 else ""
    whole, frac = f"{abs(v):.2f}".split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}₹{whole}.{frac}"

class DalaliService:

    @staticmethod
    def get_next_dalali_number() -> int:
        """
        Get the next dalali number
        """
        dalali_entry = DalaliEntry.query.order_by(DalaliEntry.dalali_number.desc()).first()
        return dalali_entry.dalali_number + 1 if dalali_entry else 1

    @staticmethod
    def create_dalali_entry(data: Dict[str, Any]) -> Tuple[bool, Union[DalaliEntry, str]]:
        """
        Create a new dalali entry with associated records
        Returns: (success, dalali_entry or error_message)
        """
        try:
            # Start a transaction
            # Extract and format the other_details from less_details
            other_details_data = (data.get("less_details") or {}).get("other_details", [])
            
            dalali_entry = DalaliEntry(
                dalali_number=data.get("dalali_number"),
                supplier_id=data.get("supplier_id"),
                register_date=data.get("register_date"),
                amount=data.get("amount"),
                deduction=data.get("deduction"),
                tds_deduction=data.get("tds_deduction"),
                other_deduction=data.get("other_deduction"),
                settlement_deduction=data.get("settlement_deduction"),
                gst_addition=data.get("gst_addition"),
                other_details=json.dumps(other_details_data),
                notes=json.dumps(data.get("notes") or []),
                type=data.get("type"),  # Validation already done in schema
                status=data.get("status"),  # Validation already done in schema
                reference_page_number=data.get("reference_page_number"),
                tally_bill_no=data.get("tally_bill_no"),
                created_by=data.get("created_by")
            )
            print("after dalali_entry")
            db.session.add(dalali_entry)
            db.session.flush()  # Get the ID without committing
            
            # Add dalali bills
            if data.get("dalali_bills"):
                for bill_data in data["dalali_bills"]:
                    dalali_bill = DalaliBills(
                        dalali_id=dalali_entry.id,
                        memo_id=bill_data.get("memo_id"),  # Using id directly from our schema
                        created_by=data.get("created_by")
                    )
                    db.session.add(dalali_bill)
            
            if data.get("type") == "Part":
                part_dalali = PartDalali(
                    dalali_id=dalali_entry.id,
                    supplier_id=data.get("supplier_id"),
                    used=False,
                    use_dalali_id=None,
                    created_by=data.get("created_by"),
                    last_updated_by=data.get("created_by")
                )
                db.session.add(part_dalali)

            print("after dalali_bills")
            # Add part dalali entries
            if data.get("part_dalali"):
                for part_data in data["part_dalali"]:
                    part_dalali = db.session.query(PartDalali).filter_by(id=part_data.get("id")).first()
                    if part_dalali:
                        part_dalali.used = True
                        part_dalali.use_dalali_id = dalali_entry.id
                        part_dalali.last_updated_by = data.get("created_by")
                        part_dalali.last_updated = datetime.now()
                    else: 
                        raise DataError(f"Part dalali entry not found for dalali number: {part_data.get('id')}")
            
            print("after part_dalali")
            # Add sender payments
            if data.get("dalali_sender_payments"):
                for payment_data in data["dalali_sender_payments"]:
                    sender_payment = DalaliSenderPayments(
                        dalali_id=dalali_entry.id,
                        bank_id=payment_data.get("bank_id"),
                        amount=payment_data.get("amount"),
                        cheque_number=payment_data.get("cheque_number"),
                        cheque_date=payment_data.get("cheque_date") or None,
                        created_by=data.get("created_by")
                    )
                    db.session.add(sender_payment)
            
            print("after dalali_sender_payments")
            # Add receiver payments
            if data.get("dalali_receiver_payments"):
                for payment_data in data["dalali_receiver_payments"]:
                    receiver_payment = DalaliReceiverPayments(
                        dalali_id=dalali_entry.id,
                        firm_id=payment_data.get("firm_id"),
                        firm_bank_id=payment_data.get("firm_bank_id"),
                        amount=payment_data.get("amount"),
                        received_date=payment_data.get("received_date"),
                        cheque_number=payment_data.get("cheque_number"),
                        created_by=data.get("created_by")
                    )
                    db.session.add(receiver_payment)
            
            print("after dalali_receiver_payments")
            # Add TDS details
            if data.get("tds_details"):
                for tds_data in data["tds_details"]:
                    tds_detail = TdsDetails(
                        dalali_id=dalali_entry.id,
                        amount=tds_data.get("amount"),
                        notes=tds_data.get("notes"),
                        checked=tds_data.get("checked"),
                        created_by=data.get("created_by")
                    )
                    db.session.add(tds_detail)
            
            print("after tds_details")
            db.session.flush()
            DalaliService._apply_invoice(dalali_entry, data, previous_status=None)
            # Commit the transaction
            db.session.commit()

            print("after commit")
            return True, dalali_entry
        except DataError as e:
            db.session.rollback()
            return False, e.dict().get("message", str(e))
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating dalali entry: {str(e)}"

    @staticmethod
    def update_dalali_entry(dalali_id: int, data: Dict[str, Any]) -> Tuple[bool, Union[DalaliEntry, str]]:
        """
        Update an existing dalali entry with all associated records
        Returns: (success, dalali_entry or error_message)
        """
        try:
            # Start a transaction
            dalali_entry = DalaliEntry.query.get(dalali_id)
            if not dalali_entry:
                return False, "Dalali entry not found"
            previous_status = dalali_entry.status
            
            # Update main entry fields
            if data.get("dalali_number") is not None:
                dalali_entry.dalali_number = data.get("dalali_number")
            if data.get("supplier_id") is not None:
                dalali_entry.supplier_id = data.get("supplier_id")
            if data.get("register_date") is not None:
                dalali_entry.register_date = data.get("register_date")
            if data.get("amount") is not None:
                dalali_entry.amount = data.get("amount")
            if data.get("deduction") is not None:
                dalali_entry.deduction = data.get("deduction")
            if data.get("tds_deduction") is not None:
                dalali_entry.tds_deduction = data.get("tds_deduction")
            if data.get("other_deduction") is not None:
                dalali_entry.other_deduction = data.get("other_deduction")
            if data.get("settlement_deduction") is not None:
                dalali_entry.settlement_deduction = data.get("settlement_deduction")
            if data.get("gst_addition") is not None:
                dalali_entry.gst_addition = data.get("gst_addition")
            if data.get("less_details") is not None:
                # Extract and format the other_details from less_details consistently
                other_details_data = (data.get("less_details") or {}).get("other_details", [])
                dalali_entry.other_details = json.dumps(other_details_data)
            if data.get("notes") is not None:
                dalali_entry.notes = json.dumps(data.get("notes", []))
            if data.get("type") is not None:
                dalali_entry.type = data.get("type")  # Validation already done in schema
            if data.get("status") is not None:
                dalali_entry.status = data.get("status")  # Validation already done in schema
            if data.get("reference_page_number") is not None:
                dalali_entry.reference_page_number = data.get("reference_page_number")
            if data.get("tally_bill_no") is not None:
                dalali_entry.tally_bill_no = data.get("tally_bill_no")
            
            dalali_entry.last_updated_by = data.get("last_updated_by")
            dalali_entry.last_updated = datetime.now()
            
            # Update sender payments
            if data.get("dalali_sender_payments") is not None:
                # Remove existing sender payments
                for payment in dalali_entry.dalali_sender_payments:
                    db.session.delete(payment)
                
                # Add new sender payments
                for payment_data in data["dalali_sender_payments"]:
                    sender_payment = DalaliSenderPayments(
                        dalali_id=dalali_entry.id,
                        bank_id=payment_data.get("bank_id"),
                        amount=payment_data.get("amount"),
                        cheque_number=payment_data.get("cheque_number"),
                        cheque_date=payment_data.get("cheque_date") or None,
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(sender_payment)
            
            # Update receiver payments
            if data.get("dalali_receiver_payments") is not None:
                # Remove existing receiver payments
                for payment in dalali_entry.dalali_receiver_payments:
                    db.session.delete(payment)
                
                # Add new receiver payments
                for payment_data in data["dalali_receiver_payments"]:
                    receiver_payment = DalaliReceiverPayments(
                        dalali_id=dalali_entry.id,
                        firm_id=payment_data.get("firm_id"),
                        firm_bank_id=payment_data.get("firm_bank_id"),
                        amount=payment_data.get("amount"),
                        received_date=payment_data.get("received_date"),
                        cheque_number=payment_data.get("cheque_number"),
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(receiver_payment)
            
            # Update TDS details
            if data.get("tds_details") is not None:
                # Remove existing TDS details
                for tds in dalali_entry.tds_details:
                    db.session.delete(tds)
                
                # Add new TDS details
                for tds_data in data["tds_details"]:
                    tds_detail = TdsDetails(
                        dalali_id=dalali_entry.id,
                        amount=tds_data.get("amount"),
                        notes=tds_data.get("notes"),
                        checked=tds_data.get("checked"),
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(tds_detail)
            
            db.session.flush()
            DalaliService._apply_invoice(dalali_entry, data, previous_status=previous_status)
            # Commit the transaction
            db.session.commit()
            return True, dalali_entry
        except DataError as e:
            db.session.rollback()
            return False, e.dict().get("message", str(e))
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating dalali entry: {str(e)}"

    # ------------------------------------------------------------------
    # Tax invoice
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_invoice(entry: DalaliEntry, data: Dict[str, Any], previous_status: Optional[str]) -> None:
        """
        Store the billing firm / bank / bill date / invoice number and work out
        the GST block on the server. The block is frozen once the entry is
        Approved: later edits (or memo changes) never change an issued invoice.
        """
        if previous_status == "Approved" and entry.gst_rate is not None:
            # Issued invoice: nothing on it changes. Move it back to Pending to correct it.
            entry.amount, entry.gst_addition = DalaliService._frozen_amounts(entry, data)
            return
        for key in ("billing_firm_id", "billing_firm_bank_id", "bill_date", "invoice_number", "place_of_supply"):
            if key in data and data.get(key) is not None:
                setattr(entry, key, data[key])
        if data.get("gst_rate") is not None:
            try:
                entry.gst_rate = gst_invoice.normalize_rate(data["gst_rate"])
            except ValueError as e:
                raise DataError(str(e))

        if entry.billing_firm_bank_id and entry.billing_firm_id:
            bank = db.session.get(FirmBank, entry.billing_firm_bank_id)
            if not bank or bank.firm_id != entry.billing_firm_id:
                raise DataError("The firm bank chosen does not belong to the billing firm")
        if entry.bill_date is None and entry.billing_firm_id:
            rd = entry.register_date
            entry.bill_date = rd.date() if isinstance(rd, datetime) else rd

        if entry.gst_rate is None:
            return  # an old bill: GST was typed in by hand (gst_addition)

        if not entry.billing_firm_id:
            raise DataError("Choose the firm this dalali bill is raised from")
        firm = db.session.get(Firm, entry.billing_firm_id)
        if firm is None:
            raise DataError("Billing firm not found")
        rate = gst_invoice.Decimal(entry.gst_rate)
        firm_state = gst_invoice.state_from_gstin(firm.gstin)
        if rate > 0 and not firm_state:
            raise DataError(f"{firm.name} has no valid GSTIN, so GST can't be charged. Pick 'No GST' or add the firm's GSTIN.")

        # Taxable value: the memos' commission (Full) or the typed amount (Part).
        if entry.type == "Part":
            if data.get("taxable_amount") is not None:
                taxable = data["taxable_amount"]
            elif entry.taxable_amount is not None:
                taxable = entry.taxable_amount
            else:
                raise DataError("Enter the commission amount being billed")
        else:
            bills = DalaliBills.query.filter_by(dalali_id=entry.id).all()
            taxable = sum((b.memo_entry.commision or 0) for b in bills if b.memo_entry)

        if not entry.place_of_supply:
            supplier = db.session.get(Supplier, entry.supplier_id)
            entry.place_of_supply = gst_invoice.supplier_state(
                supplier.gstin if supplier else None, supplier.pin_code if supplier else None
            )["code"]

        block = gst_invoice.compute(taxable, rate, firm_state, entry.place_of_supply)
        for key in ("taxable_amount", "cgst_amount", "sgst_amount", "igst_amount", "round_off", "grand_total"):
            setattr(entry, key, block[key])

        # The entry's net amount = what the screen sent, re-based on the
        # server's GST (tax + round off) so the two can never disagree.
        new_addition = int(round(float(block["grand_total"] - block["taxable_amount"])))
        if "amount" in data and data.get("amount") is not None:
            sent_addition = data.get("gst_addition") or 0
            entry.amount = int(round(float(data["amount"]) - float(sent_addition) + new_addition))
        else:
            entry.amount = int(round(float(entry.amount or 0) - float(entry.gst_addition or 0) + new_addition))
        entry.gst_addition = new_addition

        if not entry.invoice_number:
            entry.invoice_number = DalaliService.next_invoice_number(entry.billing_firm_id, entry.bill_date, exclude_id=entry.id)
        DalaliService._check_invoice_number_free(entry)

    @staticmethod
    def _frozen_amounts(entry: DalaliEntry, data: Dict[str, Any]):
        """Net amount of an approved invoice after an edit: its frozen GST, re-based like a normal save."""
        frozen = int(round(float((entry.grand_total or 0) - (entry.taxable_amount or 0))))
        if data.get("amount") is not None:
            sent = data.get("gst_addition") or 0
            return int(round(float(data["amount"]) - float(sent) + frozen)), frozen
        return entry.amount, frozen

    @staticmethod
    def _fy_bounds(d):
        from datetime import date as _date
        start_year = d.year if d.month >= 4 else d.year - 1
        return _date(start_year, 4, 1), _date(start_year + 1, 3, 31)

    @staticmethod
    def _check_invoice_number_free(entry: DalaliEntry) -> None:
        if not (entry.invoice_number and entry.billing_firm_id and entry.bill_date):
            return
        lo, hi = DalaliService._fy_bounds(entry.bill_date)
        clash = (
            DalaliEntry.query
            .filter(DalaliEntry.billing_firm_id == entry.billing_firm_id,
                    db.func.upper(DalaliEntry.invoice_number) == entry.invoice_number.upper(),
                    DalaliEntry.bill_date >= lo, DalaliEntry.bill_date <= hi,
                    DalaliEntry.id != entry.id)
            .first()
        )
        if clash:
            raise DataError(
                f"Invoice No. {entry.invoice_number} is already used by Dalali No. {clash.dalali_number} "
                f"this financial year — use the next number"
            )

    @staticmethod
    def next_invoice_number(firm_id: int, bill_date=None, exclude_id: Optional[int] = None) -> str:
        """Next number in the firm's series for the bill date's financial year (GST-15 -> GST-16)."""
        from datetime import date as _date
        d = bill_date or _date.today()
        if isinstance(d, str):
            d = datetime.strptime(d[:10], "%Y-%m-%d").date()
        lo, hi = DalaliService._fy_bounds(d)
        q = DalaliEntry.query.filter(
            DalaliEntry.billing_firm_id == firm_id,
            DalaliEntry.invoice_number.isnot(None),
            DalaliEntry.bill_date >= lo, DalaliEntry.bill_date <= hi,
        )
        if exclude_id:
            q = q.filter(DalaliEntry.id != exclude_id)
        best, best_n = None, -1
        for (num,) in q.with_entities(DalaliEntry.invoice_number).all():
            m = gst_invoice._SUFFIX_RE.match(num.strip())
            if m and int(m.group(2)) > best_n:
                best, best_n = num, int(m.group(2))
        if best is None:
            # No bill this year yet: carry the prefix of the firm's latest number.
            last = (DalaliEntry.query
                    .filter(DalaliEntry.billing_firm_id == firm_id, DalaliEntry.invoice_number.isnot(None))
                    .order_by(DalaliEntry.bill_date.desc(), DalaliEntry.id.desc()).first())
            prefix = "GST-"
            if last:
                m = gst_invoice._SUFFIX_RE.match(last.invoice_number.strip())
                prefix = m.group(1) if m else prefix
            return f"{prefix}1"
        return gst_invoice.next_invoice_number(best)

    @staticmethod
    def invoice_defaults(supplier_id: Optional[int], firm_id: Optional[int], bill_date=None,
                         exclude_id: Optional[int] = None) -> Dict[str, Any]:
        """Everything the entry screen needs to preview the invoice."""
        out: Dict[str, Any] = {
            "states": [{"code": c, "name": n} for c, n in sorted(gst_invoice.STATE_NAMES.items())],
            "sac_code": gst_invoice.SAC_CODE,
        }
        if supplier_id:
            supplier = db.session.get(Supplier, supplier_id)
            if supplier:
                st = gst_invoice.supplier_state(supplier.gstin, supplier.pin_code)
                out.update(place_of_supply=st["code"], place_of_supply_source=st["source"],
                           supplier_gstin=supplier.gstin, default_firm_id=supplier.default_firm_id)
        if firm_id:
            firm = db.session.get(Firm, firm_id)
            if firm:
                out.update(
                    firm_state=gst_invoice.state_from_gstin(firm.gstin),
                    firm_gstin=firm.gstin,
                    next_invoice_number=DalaliService.next_invoice_number(firm_id, bill_date, exclude_id=exclude_id),
                    firm_banks=[{"id": b.id, "name": b.name, "account_number": b.account_number,
                                 "ifsc": b.ifsc, "branch": b.branch}
                                for b in FirmBank.query.filter_by(firm_id=firm_id).order_by(FirmBank.id).all()],
                )
        return out

    # ------------------------------------------------------------------
    # Approval
    # ------------------------------------------------------------------
    @staticmethod
    def approval_problem(entry: DalaliEntry) -> Optional[str]:
        """Why this entry can't be approved yet (None = it can)."""
        if entry.status == "Approved":
            return "Already approved"
        if entry.gst_rate is not None and not entry.billing_firm_id:
            return "Choose the billing firm first"
        received = sum(float(p.amount or 0) for p in entry.dalali_sender_payments)
        due = float(entry.amount or 0)
        if abs(received - due) > 0.5:
            if received < due:
                return f"Received {_fmt_inr(received)} of {_fmt_inr(due)} — {_fmt_inr(due - received)} still to record"
            return f"Received {_fmt_inr(received)} is more than the {_fmt_inr(due)} due"
        return None

    @staticmethod
    def set_status(dalali_id: int, status: str, user_id: Optional[int]) -> Tuple[bool, str]:
        entry = DalaliEntry.query.get(dalali_id)
        if not entry:
            return False, "Dalali entry not found"
        if status == "Approved":
            problem = DalaliService.approval_problem(entry)
            if problem:
                return False, problem
        elif status == "Pending":
            if entry.status != "Approved":
                return False, "Only an approved entry can be moved back to Pending"
        else:
            return False, "Status must be Approved or Pending"
        entry.status = status
        entry.last_updated_by = user_id
        entry.last_updated = datetime.now()
        db.session.commit()
        return True, f"Dalali No. {entry.dalali_number} {'approved' if status == 'Approved' else 'moved back to Pending'}"

    @staticmethod
    def bulk_approve(ids: List[int], user_id: Optional[int]) -> List[Dict[str, Any]]:
        """Approve each entry on its own; ones that aren't ready are skipped with the reason."""
        results = []
        for dalali_id in ids[:200]:
            entry = DalaliEntry.query.get(dalali_id)
            if not entry:
                results.append({"id": dalali_id, "result": "skipped", "message": "Not found"})
                continue
            ok, message = DalaliService.set_status(dalali_id, "Approved", user_id)
            results.append({
                "id": dalali_id, "dalali_number": entry.dalali_number,
                "result": "approved" if ok else "skipped", "message": message,
            })
        return results

    @staticmethod
    def get_dalali_entry(dalali_id: int) -> Optional[DalaliEntry]:
        """
        Retrieve a dalali entry with all its related data
        """
        return (
            DalaliEntry.query
            .options(db.selectinload(DalaliEntry.dalali_bills))
            .options(db.selectinload(DalaliEntry.part_dalali))
            .options(db.selectinload(DalaliEntry.dalali_sender_payments))
            .options(db.selectinload(DalaliEntry.dalali_receiver_payments))
            .options(db.selectinload(DalaliEntry.tds_details))
            .options(db.selectinload(DalaliEntry.creator))
            .options(db.selectinload(DalaliEntry.last_updater))
            .get(dalali_id)
        )

    @staticmethod
    def list_dalali_entries(
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20,
        supplier_ids: Optional[List[int]] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[DalaliEntry], int]:
        """
        List dalali entries with optional filters
        Returns: (list of entries, total count)
        """
        query = DalaliEntry.query
        
        # Apply filters
        supplier_ids = list(supplier_ids or [])
        if supplier_id:
            supplier_ids.append(supplier_id)
        if supplier_ids:
            query = query.filter(DalaliEntry.supplier_id.in_(supplier_ids))
        if search and search.strip():
            # Search every dalali entry (not just the visible page): supplier name
            # or the dalali number.
            term = search.strip()
            criterion = DalaliEntry.supplier.has(Supplier.name.ilike(f"%{term}%"))
            if term.isdigit():
                criterion = criterion | (DalaliEntry.dalali_number == int(term))
            query = query.filter(criterion)
        if status:
            query = query.filter(DalaliEntry.status == status)
        if from_date:
            query = query.filter(DalaliEntry.register_date >= from_date)
        if to_date:
            query = query.filter(DalaliEntry.register_date <= to_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        query = (
            query
            .order_by(DalaliEntry.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        
        # Load relationships
        query = (
            query
            .options(db.selectinload(DalaliEntry.dalali_bills))
            .options(db.selectinload(DalaliEntry.part_dalali))
            .options(db.selectinload(DalaliEntry.dalali_sender_payments))
            .options(db.selectinload(DalaliEntry.dalali_receiver_payments))
            .options(db.selectinload(DalaliEntry.tds_details))
            .options(db.selectinload(DalaliEntry.creator))
            .options(db.selectinload(DalaliEntry.last_updater))
            .options(db.selectinload(DalaliEntry.supplier))
        )
        
        return query.all(), total
        
    @staticmethod
    def get_unused_part_dalali_entries(
        supplier_id: int,
    ) -> Tuple[List[PartDalali], int]:
        """
        Get unused part_dalali entries for a specific supplier that have approved status
        Returns: (list of entries, total count)
        """
        if not supplier_id:
            return [], 0
            
        # Join PartDalali with its related DalaliEntry and filter for approved status
        query = (PartDalali.query
            .join(DalaliEntry, PartDalali.dalali_id == DalaliEntry.id)
            .filter(
                PartDalali.supplier_id == supplier_id,
                PartDalali.used == False,
                DalaliEntry.status == 'Approved'  # Only include approved dalali entries
            )
        )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        query = (
            query
            .order_by(PartDalali.created_at.desc())
        )
        
        # Load relationships
        query = (
            query
            .options(db.selectinload(PartDalali.dalali_entry))
            .options(db.selectinload(PartDalali.supplier))
            .options(db.selectinload(PartDalali.creator))
            .options(db.selectinload(PartDalali.last_updater))
        )
        
        return query.all(), total
        
    @staticmethod
    def delete_dalali_entry(dalali_id: int, deleted_by: int) -> Tuple[bool, str]:
        """
        Delete a dalali entry and all its associated records
        Returns: (success, success/error message)
        """
        try:
            # Start a transaction
            dalali_entry = DalaliEntry.query.get(dalali_id)
            if not dalali_entry:
                return False, "Dalali entry not found"
            
            if dalali_entry.status == "Approved":
                return False, "Cannot delete dalali entry with status 'Approved'"
            
            # Delete all related records
            # All these should cascade automatically based on foreign key constraints,
            # but we'll be explicit to ensure proper cleanup
            
            # Delete all dalali bills
            for bill in dalali_entry.dalali_bills:
                db.session.delete(bill)

            if dalali_entry.type == "Part":
                part_dalail_I_create = PartDalali.query.filter_by(
                    dalali_id=dalali_entry.id).first()
                
                if part_dalail_I_create.used == False:
                    db.session.delete(part_dalail_I_create)
                else: 
                    DataError(f"Cannot delete dalali entry with used part dalali: {part_dalail_I_create.id}")
                
            # Delete all part dalalis
            for part in dalali_entry.part_dalali:
                part.used = False
                part.use_dalali_id = None
                
            # Delete all sender payments
            for payment in dalali_entry.dalali_sender_payments:
                db.session.delete(payment)
                
            # Delete all receiver payments
            for payment in dalali_entry.dalali_receiver_payments:
                db.session.delete(payment)
                
            # Delete all TDS details
            for tds in dalali_entry.tds_details:
                db.session.delete(tds)
                
            # Delete the dalali entry itself3
            db.session.delete(dalali_entry)
            
            # Commit the transaction
            db.session.commit()
            return True, "Dalali entry deleted successfully"
        except Exception as e:
            db.session.rollback()
            raise e

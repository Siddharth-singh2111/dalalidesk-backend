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
from ..extensions import db

class DalaliService:
    @staticmethod
    def create_dalali_entry(data: Dict[str, Any]) -> Tuple[bool, Union[DalaliEntry, str]]:
        """
        Create a new dalali entry with associated records
        Returns: (success, dalali_entry or error_message)
        """
        try:
            # Start a transaction
            # Extract and format the other_details from less_details
            other_details_data = data.get("less_details", {}).get("other_details", [])
            
            dalali_entry = DalaliEntry(
                dalali_number=data.get("dalali_number"),
                supplier_id=data.get("supplier_id"),
                register_date=data.get("register_date"),
                amount=data.get("amount"),
                deduction=data.get("deduction"),
                tds_deduction=data.get("tds_deduction"),
                other_deduction=data.get("other_deduction"),
                settlement_deduction=data.get("settlement_deduction"),
                other_details=json.dumps(other_details_data),
                notes=json.dumps(data.get("notes", [])),
                type=data.get("type"),  # Validation already done in schema
                status=data.get("status"),  # Validation already done in schema
                reference_page_number=data.get("reference_page_number"),
                tally_billy_no=data.get("tally_bill_number"),
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
                        checked=tds_data.get("checked"),
                        created_by=data.get("created_by")
                    )
                    db.session.add(tds_detail)
            
            print("after tds_details")
            # Commit the transaction
            db.session.commit()

            print("after commit")
            return True, dalali_entry
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
            if data.get("less_details") is not None:
                # Extract and format the other_details from less_details consistently
                other_details_data = data.get("less_details", {}).get("other_details", [])
                dalali_entry.other_details = json.dumps(other_details_data)
            if data.get("notes") is not None:
                dalali_entry.notes = json.dumps(data.get("notes", []))
            if data.get("type") is not None:
                dalali_entry.type = data.get("type")  # Validation already done in schema
            if data.get("status") is not None:
                dalali_entry.status = data.get("status")  # Validation already done in schema
            if data.get("reference_page_number") is not None:
                dalali_entry.reference_page_number = data.get("reference_page_number")
            if data.get("tally_bill_number") is not None:
                dalali_entry.tally_billy_no = data.get("tally_bill_number")
            
            dalali_entry.last_updated_by = data.get("last_updated_by")
            dalali_entry.last_updated = datetime.now()
            
            # Update related entities - remove and recreate approach
            
            # Update dalali bills
            if data.get("dalali_bills") is not None:
                # Remove existing bills
                for bill in dalali_entry.dalali_bills:
                    db.session.delete(bill)
                
                # Add new bills
                for bill_data in data["dalali_bills"]:
                    dalali_bill = DalaliBills(
                        dalali_id=dalali_entry.id,
                        memo_id=bill_data.get("id"),  # Using id directly from our schema
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(dalali_bill)
            
            # Update part dalali entries
            if data.get("part_dalali") is not None:
                # Remove existing part dalali entries
                for part in dalali_entry.part_dalalis:
                    db.session.delete(part)
                
                # Add new part dalali entries
                for part_data in data["part_dalali"]:
                    part_dalali = PartDalali(
                        dalali_id=dalali_entry.id,
                        supplier_id=part_data.get("supplier_id"),
                        used=part_data.get("used"),
                        use_dalali_id=part_data.get("use_dalali_id"),
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(part_dalali)
            
            # Update sender payments
            if data.get("dalali_sender_payments") is not None:
                # Remove existing sender payments
                for payment in dalali_entry.sender_payments:
                    db.session.delete(payment)
                
                # Add new sender payments
                for payment_data in data["dalali_sender_payments"]:
                    sender_payment = DalaliSenderPayments(
                        dalali_id=dalali_entry.id,
                        bank_id=payment_data.get("bank_id"),
                        amount=payment_data.get("amount"),
                        cheque_number=payment_data.get("cheque_number"),
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(sender_payment)
            
            # Update receiver payments
            if data.get("dalali_receiver_payments") is not None:
                # Remove existing receiver payments
                for payment in dalali_entry.receiver_payments:
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
                        notes=tds_data.get("note"),
                        checked=tds_data.get("checked"),
                        created_by=data.get("last_updated_by"),
                        last_updated_by=data.get("last_updated_by")
                    )
                    db.session.add(tds_detail)
            
            # Commit the transaction
            db.session.commit()
            return True, dalali_entry
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating dalali entry: {str(e)}"

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
        per_page: int = 20
    ) -> Tuple[List[DalaliEntry], int]:
        """
        List dalali entries with optional filters
        Returns: (list of entries, total count)
        """
        query = DalaliEntry.query
        
        # Apply filters
        if supplier_id:
            query = query.filter(DalaliEntry.supplier_id == supplier_id)
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
        Get unused part_dalali entries for a specific supplier
        Returns: (list of entries, total count)
        """
        if not supplier_id:
            return [], 0
            
        query = PartDalali.query.filter(
            PartDalali.supplier_id == supplier_id,
            PartDalali.used == False
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
            
            # Delete all related records
            # All these should cascade automatically based on foreign key constraints,
            # but we'll be explicit to ensure proper cleanup
            
            # Delete all dalali bills
            for bill in dalali_entry.dalali_bills:
                db.session.delete(bill)
                
            # Delete all part dalalis
            for part in dalali_entry.part_dalalis:
                db.session.delete(part)
                
            # Delete all sender payments
            for payment in dalali_entry.dalali_sender_payments:
                db.session.delete(payment)
                
            # Delete all receiver payments
            for payment in dalali_entry.dalali_receiver_payments:
                db.session.delete(payment)
                
            # Delete all TDS details
            for tds in dalali_entry.tds_details:
                db.session.delete(tds)
                
            # Delete the dalali entry itself
            db.session.delete(dalali_entry)
            
            # Commit the transaction
            db.session.commit()
            return True, "Dalali entry deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting dalali entry: {str(e)}"

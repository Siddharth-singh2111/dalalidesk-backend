from typing import List, Optional, Tuple, Dict, Any, Union
from sqlalchemy.exc import IntegrityError
from sqlalchemy import exists, not_
from hca_backend.Exceptions import DataError
from ..models.memo import MemoEntry, MemoBills, PartPayments, MemoPayments
from ..models.dalali import DalaliEntry, DalaliBills
from ..models.register import RegisterEntry
from ..extensions import db

class MemoService:
    @staticmethod
    def can_delete_memo(memo_id: int) -> Tuple[bool, str]:
        """
        Check if a memo can be deleted based on business rules
        Returns: (can_delete, reason)
        """
        memo = MemoEntry.query.get(memo_id)
        if not memo:
            return False, "Memo not found"
        
        if memo.dalali_bills:
            return False, "Memo has associated dalali bills"
                
        return True, ""
    
    @staticmethod
    def delete_memo(memo_id: int, deleted_by: Optional[int] = None) -> Tuple[bool, str]:
        """
        Delete a memo and all its associated records
        Handles the resets for register entries and part payments appropriately
        Returns: (success, success/error message)
        """
        can_delete, reason = MemoService.can_delete_memo(memo_id)
        if not can_delete:
            return False, reason
            
        try:
            memo_entry = MemoEntry.query.get(memo_id)
            if not memo_entry:
                return False, "Memo entry not found"
            
            # Process each memo bill based on its type
            for bill in memo_entry.memo_bills:
                if bill.type == "PR":
                    part_payment = PartPayments.query.filter_by(memo_id=memo_id).first()
                    if part_payment:
                        if part_payment.used:
                            raise DataError(f"Cannot delete memo with used part payment. Used in Memo Number: {part_payment.use_memo.memo_number}")
                        db.session.delete(part_payment)
                else:
                    if bill.bill_id is not None:
                        register_entry = RegisterEntry.query.get(bill.bill_id)
                        if register_entry:
                            if bill.type == "F":
                                register_entry.status = "N"
                                register_entry.deduction = 0
                                register_entry.gr_amount = 0
                                register_entry.partial_amount = 0
                            elif bill.type == "D":
                                register_entry.deduction = 0
                            elif bill.type == "G":
                                register_entry.gr_amount = 0
                            
                            if deleted_by:
                                register_entry.last_updated_by = deleted_by
                
            for bill in memo_entry.memo_bills:
                db.session.delete(bill)
            
            for payment in memo_entry.memo_payments:
                db.session.delete(payment)
            
            for part_payment in memo_entry.part_payments_source:
                if part_payment.used:
                    raise DataError(f"Cannot delete memo with used part payment. Used in Memo Number: {part_payment.use_memo.memo_number}")
                db.session.delete(part_payment)
            
            for part_payment in memo_entry.part_payments_used:
                part_payment.used = False
                part_payment.use_memo_id = None
            
            db.session.delete(memo_entry)
            
            db.session.commit()
            return True, "Memo deleted successfully"
        except DataError as e:
            db.session.rollback()
            return False, e.error_dict.get("message", str(e))
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting memo: {str(e)}"
    
    
    @staticmethod
    def get_pending_memos(supplier_id: int, party_id: int = None) -> List[MemoEntry]:
        """
        Get all pending memos for a supplier.
        A memo is considered pending if it has no associated dalali bills,
        or all its associated dalali bills belong to a cancelled dalali entry.
        Uses an efficient NOT EXISTS subquery.
        """
        
        # Subquery to find any associated DalaliBill linked to a non-cancelled DalaliEntry
        subquery = exists().where(
            DalaliBills.memo_id == MemoEntry.id,
            DalaliBills.dalali_entry.has(DalaliEntry.status != 'cancelled')
        )

        # Select MemoEntries for the supplier where the subquery condition is false (NOT EXISTS)
        # Ensure database indexes exist on MemoEntry.supplier_id, DalaliBills.memo_id, 
        # DalaliBills.dalali_id, DalaliEntry.id, and DalaliEntry.status for optimal performance.
        pending_memos = MemoEntry.query.filter(
            MemoEntry.supplier_id == supplier_id,
            MemoEntry.commision != None,
            MemoEntry.less_gst_percentage != None,
            not_(subquery)
        )

        if party_id is not None:
            pending_memos = pending_memos.filter(MemoEntry.party_id == party_id)
        
        pending_memos = pending_memos.all()

        return pending_memos

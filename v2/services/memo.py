from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy import exists, not_
from ..models.memo import MemoEntry, MemoBills
from ..models.dalali import DalaliEntry, DalaliBills
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
            
        # Check if any bills have type "PR"
        for bill in memo.memo_bills:
            if bill.type == "PR":
                return False, "Cannot delete memo with PR type bills"
                
        return True, ""
    
    @staticmethod
    def delete_memo(memo_id: int) -> Tuple[bool, str]:
        """
        Delete a memo if business rules allow
        Returns: (success, message)
        """
        can_delete, reason = MemoService.can_delete_memo(memo_id)
        if not can_delete:
            return False, reason
            
        try:
            memo = MemoEntry.query.get(memo_id)
            db.session.delete(memo)
            db.session.commit()
            return True, "Memo deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting memo: {str(e)}"
    
    
    @staticmethod
    def get_pending_memos(supplier_id: int) -> List[MemoEntry]:
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
            not_(subquery)
        ).all()

        return pending_memos
    
    
    
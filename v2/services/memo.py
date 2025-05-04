from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.exc import IntegrityError
from ..models.memo import MemoEntry, MemoBills
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

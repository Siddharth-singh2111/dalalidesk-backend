from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from ..extensions import db
from ..models.audit import AuditLog
from ..core.context import get_current_user_id


def audit_before_flush(session: Session, flush_context, instances):
    """First phase of auditing - store objects that need auditing before they get IDs"""
    # Get current user ID from context
    user = get_current_user_id()

    # Store new objects for auditing after flush (when they'll have IDs)
    session._objects_to_audit_new = [obj for obj in session.new if not isinstance(obj, AuditLog)]
    
    # Store dirty objects
    session._objects_to_audit_dirty = []
    for obj in session.dirty:
        if isinstance(obj, AuditLog) or not session.is_modified(obj, include_collections=False):
            continue
            
        state = inspect(obj)
        diffs = {}
        for attr in state.attrs:
            hist = state.get_history(attr.key, True)
            if not hist.has_changes():
                continue
            # Store only the new value instead of [old, new] pairs
            diffs[attr.key] = hist.added[0] if hist.added else None
                              
        if diffs:  # Only store if there are actual changes
            session._objects_to_audit_dirty.append((obj, diffs))
    
    # Store deleted objects 
    session._objects_to_audit_deleted = [obj for obj in session.deleted if not isinstance(obj, AuditLog)]

def audit_after_flush(session: Session, flush_context):
    """Second phase of auditing - create audit records now that objects have IDs"""
    # Get current user ID from context
    user = get_current_user_id()
        
    # Handle new objects (INSERT)
    for obj in getattr(session, '_objects_to_audit_new', []):
        session.add(AuditLog(
            user_id    = user,
            table_name = obj.__tablename__,
            record_id  = obj.id,  # Now this will have a value
            action     = "INSERT",
            changes    = {c.name: getattr(obj, c.name) 
                         for c in obj.__table__.columns}
        ))
    
    # Handle dirty objects (UPDATE)
    for obj, diffs in getattr(session, '_objects_to_audit_dirty', []):
        session.add(AuditLog(
            user_id    = user,
            table_name = obj.__tablename__,
            record_id  = obj.id,
            action     = "UPDATE",
            changes    = diffs
        ))
    
    # Handle deleted objects (DELETE)
    for obj in getattr(session, '_objects_to_audit_deleted', []):
        session.add(AuditLog(
            user_id    = user,
            table_name = obj.__tablename__,
            record_id  = obj.id,
            action     = "DELETE",
            changes    = None
        ))
    
    # Clear temporary storage
    session._objects_to_audit_new = []
    session._objects_to_audit_dirty = []
    session._objects_to_audit_deleted = []

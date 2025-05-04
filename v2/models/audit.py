from ..extensions import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    table_name = db.Column(db.String)
    record_id = db.Column(db.Integer)
    action = db.Column(db.String)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    changes = db.Column(db.JSON)

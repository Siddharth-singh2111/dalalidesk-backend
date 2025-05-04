# app/__init__.py
from flask import Flask
from .extensions import db
from .api.memo import memo_bp
from .models import MemoEntry, MemoBills, Users, AuditLog
from .core.listeners import audit_before_flush, audit_after_flush

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    with app.app_context():
        db.Model.metadata.reflect(db.engine, only=['memo_entry', 'memo_bills', 'users'])
        db.event.listen(db.session, 'before_flush', audit_before_flush)
        db.event.listen(db.session, 'after_flush', audit_after_flush)

    # register blueprints
    app.register_blueprint(memo_bp)
    return app

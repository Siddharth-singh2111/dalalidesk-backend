from flask import Flask, jsonify
from flask_cors import CORS
from datetime import timedelta

import atexit
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from apscheduler.schedulers.background import BackgroundScheduler
from background_tasks import _perform_backup
import pytz

from hca_backend.v2.extensions import db
from hca_backend.v2.core.listeners import audit_before_flush, audit_after_flush
from hca_backend.v2.api import memo_bp, dalali_bp, reports_bp
from Exceptions.custom_exception import DataError as LocalDataError
from hca_backend.Exceptions import DataError as AppDataError


# Import Dalali models
from hca_backend.v2.models.dalali import (
    DalaliEntry, DalaliBills, PartDalali,
    DalaliSenderPayments, DalaliReceiverPayments, TdsDetails
)

import os

from OCR.name_cache import NameMatchCache
from OCR.ocr_queue import OCRQueue

# Import v1 blueprint
from hca_backend.v1.api import v1_bp

# Initialize queue
ocr_queue = OCRQueue()

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Register handlers for both versions of the exception
@app.errorhandler(LocalDataError)
def handle_local_data_error(e):
    error = e.dict()
    if error['status'] == 'error' and 'input_errors' not in error:
        error['input_errors'] = {}
    return jsonify(error), 500

@app.errorhandler(AppDataError)
def handle_app_data_error(e):
    error = e.dict()
    if error['status'] == 'error' and 'input_errors' not in error:
        error['input_errors'] = {}
    return jsonify(error), 500

# Enable CORS for all routes
CORS(app)

# Initialize JWT
app.config['JSON_SORT_KEYS'] = False
app.config['JWT_SECRET_KEY'] = 'NHYd198vQNOBa9HrIAGEGNYrKHBegc9Z'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=6)

jwt = JWTManager(app)

# Configure database
db_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize database
db.init_app(app)


with app.app_context():
        # Reflect existing tables
    db.Model.metadata.reflect(db.engine)
    # Create all tables from models
    db.create_all()
    # Setup event listeners
    db.event.listen(db.session, 'before_flush', audit_before_flush)
    db.event.listen(db.session, 'after_flush', audit_after_flush)



# Before request handler to store user ID in g
@app.before_request
def store_user_in_context():
    from flask import g
    from hca_backend.v1.api import get_user_id_from_token
    try:
        user_id = get_user_id_from_token()
        g.current_user_id = user_id
    except Exception:
        g.current_user_id = None

# Register blueprints
app.register_blueprint(dalali_bp)
app.register_blueprint(v1_bp)
app.register_blueprint(memo_bp)
app.register_blueprint(reports_bp)
# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True, timezone=pytz.timezone("Asia/Kolkata"))
scheduler.add_job(func=_perform_backup, trigger="interval", hours=24)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    # Important: Disable reloader when using APScheduler in debug mode
    # otherwise the scheduler might run twice.
    # Set use_reloader=False when running with 'flask run'
    # or pass it to app.run directly if using that.
    app.run(debug=True, use_reloader=False)

from flask import Blueprint, jsonify, request, abort
from ..schemas.memo import MemoEntrySchema, MemoEntryCreate, MemoEntryUpdate
from ..models.memo import MemoEntry
from ..services.memo import MemoService
from ..extensions import db
from pydantic import ValidationError
from hca_backend.API_Database.retrieve_memo_dalali import calculate_commission, get_commission_rate
from hca_backend.Exceptions import DataError

memo_bp = Blueprint("memo", __name__, url_prefix="/api/memo")

@memo_bp.route("/<int:memo_id>", methods=["GET"])
def get_memo(memo_id):
    entry = (
        MemoEntry.query
        .options(db.selectinload(MemoEntry.memo_bills))
        .options(db.selectinload(MemoEntry.creator))
        .options(db.selectinload(MemoEntry.last_updater))
        .get(memo_id)
    )
    if not entry:
        abort(404, description="Memo not found")
    
    # Convert SQLAlchemy object to Pydantic model
    schema = MemoEntrySchema.model_validate(entry)
    return jsonify(schema.model_dump())

@memo_bp.route("/", methods=["POST"])
def create_memo():
    try:
        # Validate incoming data with Pydantic
        schema = MemoEntryCreate.model_validate(request.json)
        data = schema.model_dump()
        
        # Create SQLAlchemy object
        entry = MemoEntry(**data)
        db.session.add(entry)
        db.session.commit()
        
        # Return validated response
        return jsonify(MemoEntrySchema.model_validate(entry).model_dump())
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

@memo_bp.route("/<int:memo_id>", methods=["DELETE"])
def delete_memo(memo_id):
    success, message = MemoService.delete_memo(memo_id)
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@memo_bp.route("/pending/<int:supplier_id>", methods=["GET"])
def get_pending_memos(supplier_id):
    memos = MemoService.get_pending_memos(supplier_id)
    return jsonify([MemoEntrySchema.model_validate(memo).model_dump() for memo in memos])

@memo_bp.route("/<int:memo_id>/commission", methods=["POST"])
def update_memo_commission(memo_id):
    """
    Update the commission information for a memo entry using calculate_commission function.
    
    Parameters expected in request body:
    - gst_percentage: float (optional, default 4.762)
    """
    # Get the memo entry
    entry = MemoEntry.query.get_or_404(memo_id)
    
    # Get GST percentage from request or use default
    data = request.json or {}
    gst_percentage = data.get('gst_percentage', 4.762)
    
    # Use calculate_commission function to calculate values
    try:
        rate_percent = get_commission_rate(entry.supplier_id, entry.party_id)
        result = calculate_commission(entry.amount, gst_percentage, rate_percent)
    except DataError as e:
        return jsonify({"error": str(e)}), 400
    
    # Update the memo entry
    entry.less_gst_percentage = 5
    entry.less_gst = result['amount_without_gst']
    entry.commision = result['commission']
    
    # Save changes
    db.session.commit()
    
    # Return the updated memo
    schema = MemoEntrySchema.model_validate(entry)
    return jsonify(schema.model_dump())

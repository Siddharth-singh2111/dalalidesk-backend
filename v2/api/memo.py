from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required
from ..schemas.memo import MemoEntrySchema, MemoEntryCreate, MemoEntryUpdate
from ..models.memo import MemoEntry
from ..services.memo import MemoService
from ..extensions import db
from pydantic import ValidationError
from hca_backend.API_Database.retrieve_memo_dalali import calculate_commission, get_commission_rate
from hca_backend.Exceptions import DataError
from hca_backend.v1.api.routes import permission_required

memo_bp = Blueprint("memo", __name__, url_prefix="/api/memo")

@memo_bp.route("/<int:memo_id>", methods=["GET"])
@jwt_required()
@permission_required("memo_entry", "read")
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
@jwt_required()
@permission_required("memo_entry", "create")
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
@jwt_required()
@permission_required("memo_entry", "delete")
def delete_memo(memo_id):
    success, message = MemoService.delete_memo(memo_id)
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 400

@memo_bp.route("/pending/<int:supplier_id>", methods=["GET"])
@jwt_required()
@permission_required("memo_entry", "read")
def get_pending_memos(supplier_id):
    memos = MemoService.get_pending_memos(supplier_id)
    return jsonify([MemoEntrySchema.model_validate(memo).model_dump() for memo in memos])

@memo_bp.route("/<int:memo_id>/commission", methods=["POST"])
@jwt_required()
@permission_required("memo_entry", "update")
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


# ---------------------------------------------------------------------------
# Memo edit (ported from GHT): same create-shaped payload as POST /add/memo_entry.
# PUT saves; POST .../preview does the same work, rolls back and returns the
# before/after of every bill. Anyone with memo Edit rights, any time (DM owner,
# 2026-10-25); memos in a dalali bill or marked paid are refused.
# ---------------------------------------------------------------------------
def _memo_edit(memo_id: int, dry_run: bool):
    from hca_backend.Entities.MemoEntry import edit_memo
    if not MemoEntry.query.get(memo_id):
        return jsonify({"status": "error", "message": "Memo not found"}), 404
    try:
        result = edit_memo(memo_id, request.json or {}, dry_run=dry_run)
    except DataError as e:
        info = e.dict() if isinstance(e.dict(), dict) else {"message": str(e)}
        return jsonify({"status": "error", "message": info.get("message", str(e))}), 400
    if result.get("status") != "okay":
        return jsonify(result), 400
    return jsonify(result), 200


@memo_bp.route("/<int:memo_id>", methods=["PUT"])
@jwt_required()
@permission_required("memo_entry", "update")
def edit_memo_route(memo_id):
    return _memo_edit(memo_id, dry_run=False)


@memo_bp.route("/<int:memo_id>/preview", methods=["POST"])
@jwt_required()
@permission_required("memo_entry", "update")
def preview_memo_edit(memo_id):
    return _memo_edit(memo_id, dry_run=True)


@memo_bp.route("/<int:memo_id>/can_edit", methods=["GET"])
@jwt_required()
@permission_required("memo_entry", "read")
def can_edit_memo(memo_id):
    from hca_backend.API_Database.retrieve_memo_dalali import get_memo_dalali_payment, is_memo_used_by_dalali
    if is_memo_used_by_dalali(memo_id):
        return jsonify({"can_edit": False, "reason": "This memo is in a dalali bill. Remove it from the dalali bill first."})
    paid = get_memo_dalali_payment(memo_id)
    if paid and paid.get("is_paid"):
        return jsonify({"can_edit": False, "reason": "This memo's commission is marked paid."})
    return jsonify({"can_edit": True, "reason": None})

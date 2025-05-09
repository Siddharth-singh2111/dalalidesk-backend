from flask import Blueprint, jsonify, request, abort
from ..schemas.memo import MemoEntrySchema, MemoEntryCreate, MemoEntryUpdate
from ..models.memo import MemoEntry
from ..services.memo import MemoService
from ..extensions import db
from pydantic import ValidationError

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
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400

@memo_bp.route("/pending/<int:supplier_id>", methods=["GET"])
def get_pending_memos(supplier_id):
    memos = MemoService.get_pending_memos(supplier_id)
    return jsonify([MemoEntrySchema.model_validate(memo).model_dump() for memo in memos])
from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required

from hca_backend.v2.core.context import get_current_user_id
from ..schemas.dalali import (
    DalaliEntrySchema, DalaliEntryCreate, DalaliEntryUpdate
)
from ..models.dalali import DalaliEntry
from ..services.dalali import DalaliService
from ..extensions import db
from pydantic import ValidationError
import json

dalali_bp = Blueprint("dalali", __name__, url_prefix="/dalali")

@jwt_required()
@dalali_bp.route("/<int:dalali_id>", methods=["GET"])
def get_dalali(dalali_id):
    """Get a specific dalali entry by ID"""
    entry = DalaliService.get_dalali_entry(dalali_id)
    if not entry:
        abort(404, description="Dalali entry not found")
    
    # Convert SQLAlchemy object to Pydantic model
    schema = DalaliEntrySchema.model_validate(entry)
    
    # Process JSON fields
    if entry.notes:
        try:
            schema.notes = json.loads(entry.notes)
        except:
            schema.notes = []
    
    if entry.other_details:
        try:
            schema.less_details = {"other_details": json.loads(entry.other_details)}
        except:
            schema.less_details = {"other_details": []}
    
    return jsonify(schema.model_dump())

@jwt_required()
@dalali_bp.route("/", methods=["GET"])
def list_dalali():
    """List dalali entries with optional filters"""
    # Get filter parameters
    supplier_id = request.args.get("supplier_id", type=int)
    status = request.args.get("status")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Get entries from service
    entries, total = DalaliService.list_dalali_entries(
        supplier_id=supplier_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page
    )
    
    # Convert to schema
    result = []
    for entry in entries:
        schema = DalaliEntrySchema.model_validate(entry)
        
        # Process JSON fields
        if entry.notes:
            try:
                schema.notes = json.loads(entry.notes)
            except:
                schema.notes = []
        
        if entry.other_details:
            try:
                schema.less_details = {"other_details": json.loads(entry.other_details)}
            except:
                schema.less_details = {"other_details": []}
        
        result.append(schema.model_dump())
    
    return jsonify({
        "items": result,
        "total": total,
        "page": page,
        "per_page": per_page
    })

@jwt_required()
@dalali_bp.route("/", methods=["POST"])
def create_dalali():
    """Create a new dalali entry"""
    try:
        # Validate incoming data with Pydantic
        current_user_id = get_current_user_id()
        request.json["created_by"] = current_user_id

        schema = DalaliEntryCreate.model_validate(request.json)
        data = schema.model_dump()
        
        # Create entry using service
        success, result = DalaliService.create_dalali_entry(data)
        
        if not success:
            return jsonify({"error": result}), 400
        
        # Return created entry
        entry_schema = DalaliEntrySchema.model_validate(result)
        
        # Process JSON fields
        if result.notes:
            try:
                entry_schema.notes = json.loads(result.notes)
            except:
                entry_schema.notes = []
        
        if result.other_details:
            try:
                entry_schema.less_details = {"other_details": json.loads(result.other_details)}
            except:
                entry_schema.less_details = {"other_details": []}
        
        return jsonify(entry_schema.model_dump()), 201
    
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@jwt_required()
@dalali_bp.route("/<int:dalali_id>", methods=["PUT"])
def update_dalali(dalali_id):
    """Update an existing dalali entry"""
    try:
        # Validate incoming data with Pydantic
        current_user_id = get_current_user_id()
        request.json["last_updated_by"] = current_user_id

        schema = DalaliEntryUpdate.model_validate(request.json)
        data = schema.model_dump()
        
        # Update entry using service
        success, result = DalaliService.update_dalali_entry(dalali_id, data)
        
        if not success:
            return jsonify({"error": result}), 400
        
        # Return updated entry
        entry_schema = DalaliEntrySchema.model_validate(result)
        
        # Process JSON fields
        if result.notes:
            try:
                entry_schema.notes = json.loads(result.notes)
            except:
                entry_schema.notes = []
        
        if result.other_details:
            try:
                entry_schema.less_details = {"other_details": json.loads(result.other_details)}
            except:
                entry_schema.less_details = {"other_details": []}
        
        return jsonify(entry_schema.model_dump())
    
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

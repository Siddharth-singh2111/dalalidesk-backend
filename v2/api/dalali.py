from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_jwt_extended import JWTManager, get_jwt
from flask_jwt_extended import create_refresh_token, verify_jwt_in_request
from sqlalchemy.exc import IntegrityError
import re

from hca_backend.v2.core.context import get_current_user_id

from ..schemas.dalali import (
    DalaliEntrySchema, DalaliEntryCreate, DalaliEntryUpdate, PartDalaliSchema
)
from ..models.dalali import DalaliEntry
from ..services.dalali import DalaliService
from ..extensions import db
from pydantic import ValidationError
import json

dalali_bp = Blueprint("dalali", __name__, url_prefix="/api/dalali")

# Only these people approve dalali entries (owner's decision 2026-10-25:
# Dhruv, Rajesh and Priyanka). Keep in step with the frontend list in
# src/config/approvers.ts. Env DALALI_APPROVERS (comma-separated) overrides.
import os
_APPROVERS = {
    u.strip().lower()
    for u in (os.getenv("DALALI_APPROVERS") or "dhruv,rajesh,priyanka").split(",")
    if u.strip()
}


def _can_approve() -> bool:
    try:
        from hca_backend.Individual import User
        username = get_jwt_identity()
        user = User.get_by_username(username) if username else None
    except Exception:
        return False
    if not user or not getattr(user, "is_active", True):
        return False
    return str(user.username).lower() in _APPROVERS


def _approval_guard(current_status, new_status):
    """Approving, un-approving or editing an approved entry is for approvers only."""
    touches_approval = (new_status == "Approved" and current_status != "Approved") or current_status == "Approved"
    if touches_approval and not _can_approve():
        return jsonify({"error": "Only Dhruv, Rajesh or Priyanka can approve or change an approved dalali entry"}), 403
    return None


def _entry_json(entry):
    schema = DalaliEntrySchema.model_validate(entry)
    if entry.notes:
        try:
            schema.notes = json.loads(entry.notes)
        except Exception:
            schema.notes = []
    schema.less_details = entry.less_details
    schema.approval_problem = DalaliService.approval_problem(entry) if entry.status != "Approved" else None
    return schema.model_dump()

@dalali_bp.route("/<int:dalali_id>", methods=["DELETE"])
@jwt_required()
def delete_dalali(dalali_id):
    """Delete a dalali entry"""
    try:
        # Get current user ID for deletion tracking
        current_user_id = get_current_user_id()
        
        # Delete entry using service
        success, message = DalaliService.delete_dalali_entry(dalali_id, current_user_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404 if "not found" in message.lower() else 400
        
        # Return success response
        return jsonify({"message": message}), 200
    
    except IntegrityError as e:
        # Handle foreign key violations
        return jsonify({
            'status': 'error',
            'message': "Dalai entry has a Dalali Settlemnt Memo Entry",
        }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@dalali_bp.route("/<int:dalali_id>", methods=["GET"])
@jwt_required()
def get_dalali(dalali_id):
    """Get a specific dalali entry by ID"""
    entry = DalaliService.get_dalali_entry(dalali_id)

    if not entry:
        abort(404, description="Dalali entry not found")
    
    return jsonify(_entry_json(entry))

@dalali_bp.route("/", methods=["GET"])
@jwt_required()
def list_dalali():
    """List dalali entries with optional filters"""

    # Get filter parameters
    supplier_id = request.args.get("supplier_id", type=int)
    status = request.args.get("status")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    supplier_ids = [int(x) for x in (request.args.get("supplier_ids") or "").split(",") if x.strip().isdigit()]
    search = request.args.get("search")
    
    # Get entries from service
    entries, total = DalaliService.list_dalali_entries(
        supplier_id=supplier_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
        supplier_ids=supplier_ids,
        search=search,
    )
    
    # Convert to schema
    result = [_entry_json(entry) for entry in entries]
    
    return jsonify({
        "items": result,
        "total": total,
        "page": page,
        "per_page": per_page
    })

@dalali_bp.route("/", methods=["POST"])
@jwt_required()
def create_dalali():
    """Create a new dalali entry"""
    try:
        # Validate incoming data with Pydantic
        current_user_id = get_current_user_id()
        request.json["created_by"] = current_user_id
        schema = DalaliEntryCreate.model_validate(request.json)
        data = schema.model_dump()
        denied = _approval_guard(None, data.get("status"))
        if denied:
            return denied
        
        # Create entry using service
        success, result = DalaliService.create_dalali_entry(data)
        
        if not success:
            return jsonify({"error": result}), 400
        
        print("after create dalali entry")
        # Return created entry
        entry_schema = DalaliEntrySchema.model_validate(result)
        
        # Process JSON fields
        if result.notes:
            try:
                entry_schema.notes = json.loads(result.notes)
            except:
                entry_schema.notes = []
        
        # Use the hybrid property for less_details
        entry_schema.less_details = result.less_details
        
        return jsonify(entry_schema.model_dump()), 201
    
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dalali_bp.route("/<int:dalali_id>", methods=["PUT"])
@jwt_required()
def update_dalali(dalali_id):
    """Update an existing dalali entry"""
    try:
        # Validate incoming data with Pydantic
        current_user_id = get_current_user_id()
        request.json["last_updated_by"] = current_user_id

        schema = DalaliEntryUpdate.model_validate(request.json)
        data = schema.model_dump()
        existing = DalaliEntry.query.get(dalali_id)
        if existing is not None:
            denied = _approval_guard(existing.status, data.get("status") or existing.status)
            if denied:
                return denied
        
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
        
        # Use the hybrid property for less_details
        entry_schema.less_details = result.less_details
        
        return jsonify(entry_schema.model_dump())
    
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dalali_bp.route("/unused-part-dalali/<int:supplier_id>", methods=["GET"])
@jwt_required()
def list_unused_part_dalali(supplier_id:int):
    """List unused part_dalali entries for a specific supplier"""
    
    # Get entries from service
    entries, total = DalaliService.get_unused_part_dalali_entries(
        supplier_id=supplier_id,
    )
    
    # Convert to schema
    result = []
    for entry in entries:
        schema = PartDalaliSchema.model_validate(entry)
        result.append(schema.model_dump())
    
    return jsonify({
        "items": result,
        "total": total,
    })

@dalali_bp.route("/get_next_available_dalali_number", methods=["GET"])
@jwt_required()
def get_next_dalali_number():
    """Get the next dalali number"""
    dalali_number = DalaliService.get_next_dalali_number()
    return jsonify({"dalali_number": dalali_number})

@dalali_bp.route("/get_all_dalali_entries_with_names", methods=["GET"])
@jwt_required()
def get_all_dalali_entries_with_names():
    """Get all dalali entries with supplier names"""
    try:
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
            
            # Use the hybrid property for less_details
            schema.less_details = entry.less_details
            
            result.append(schema.model_dump())
        
        return jsonify({
            "status": "success",
            "data": {
                "result": result,
                "total": total,
                "page": page,
                "per_page": per_page
            }
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dalali_bp.route("/invoice-defaults", methods=["GET"])
@jwt_required()
def invoice_defaults():
    """Place of supply, the firm's banks and the next invoice number, for the entry screen."""
    return jsonify(DalaliService.invoice_defaults(
        supplier_id=request.args.get("supplier_id", type=int),
        firm_id=request.args.get("firm_id", type=int),
        bill_date=request.args.get("bill_date") or None,
        exclude_id=request.args.get("exclude_id", type=int),
    ))


@dalali_bp.route("/<int:dalali_id>/approve", methods=["POST"])
@jwt_required()
def approve_dalali(dalali_id):
    if not _can_approve():
        return jsonify({"error": "You can't approve dalali entries"}), 403
    ok, message = DalaliService.set_status(dalali_id, "Approved", get_current_user_id())
    return jsonify({"message": message} if ok else {"error": message}), (200 if ok else 400)


@dalali_bp.route("/<int:dalali_id>/unapprove", methods=["POST"])
@jwt_required()
def unapprove_dalali(dalali_id):
    if not _can_approve():
        return jsonify({"error": "You can't change approvals"}), 403
    ok, message = DalaliService.set_status(dalali_id, "Pending", get_current_user_id())
    return jsonify({"message": message} if ok else {"error": message}), (200 if ok else 400)


@dalali_bp.route("/bulk-approve", methods=["POST"])
@jwt_required()
def bulk_approve_dalali():
    if not _can_approve():
        return jsonify({"error": "You can't approve dalali entries"}), 403
    ids = [int(i) for i in (request.json or {}).get("ids", []) if str(i).isdigit()]
    if not ids:
        return jsonify({"error": "No entries selected"}), 400
    results = DalaliService.bulk_approve(ids, get_current_user_id())
    return jsonify({
        "results": results,
        "approved": sum(1 for r in results if r["result"] == "approved"),
        "skipped": sum(1 for r in results if r["result"] == "skipped"),
    })

"""
API endpoints for Dispatch (digitised Dispatch Pad).

    POST   /api/dispatch                 create a dispatch (+ bills)
    GET    /api/dispatch                 list/filter dispatches
    GET    /api/dispatch/<id>            fetch one
    DELETE /api/dispatch/<id>            delete one
    GET    /api/dispatch/transports      distinct transport names (autocomplete)
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..core.context import get_current_user_id
from ..services.dispatch import DispatchService

dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/api/dispatch")


@dispatch_bp.route("", methods=["POST"])
@jwt_required()
def create_dispatch():
    """Create a dispatch and its bills."""
    data = request.json or {}
    data["created_by"] = get_current_user_id()
    ok, message, dispatch_id = DispatchService.create_dispatch(data)
    if not ok:
        return jsonify({"status": "error", "message": message}), 400
    return jsonify({"status": "okay", "message": message, "id": dispatch_id})


@dispatch_bp.route("", methods=["GET"])
@jwt_required()
def list_dispatches():
    """List dispatches, optionally filtered by party_id / from / to."""
    dispatches = DispatchService.list_dispatches(
        party_id=request.args.get("party_id", type=int),
        from_date=request.args.get("from"),
        to_date=request.args.get("to"),
    )
    return jsonify(dispatches)


@dispatch_bp.route("/transports", methods=["GET"])
@jwt_required()
def list_transports():
    """Distinct transport names for autocomplete + the report's transport filter."""
    return jsonify(DispatchService.distinct_transports())


@dispatch_bp.route("/available-bills", methods=["GET"])
@jwt_required()
def available_bills():
    """
    Bills for a party to pull into a dispatch.
    Query: party_id (required), date (single day) OR from/to (feeding-date range).
    """
    party_id = request.args.get("party_id", type=int)
    if not party_id:
        return jsonify({"status": "error", "message": "party_id is required"}), 400
    bills = DispatchService.available_bills(
        party_id=party_id,
        day=request.args.get("date"),
        from_date=request.args.get("from"),
        to_date=request.args.get("to"),
    )
    return jsonify(bills)


@dispatch_bp.route("/<int:dispatch_id>", methods=["GET"])
@jwt_required()
def get_dispatch(dispatch_id: int):
    dispatch = DispatchService.get_dispatch(dispatch_id)
    if not dispatch:
        return jsonify({"status": "error", "message": "Dispatch not found"}), 404
    return jsonify(dispatch)


@dispatch_bp.route("/<int:dispatch_id>", methods=["DELETE"])
@jwt_required()
def delete_dispatch(dispatch_id: int):
    ok, message = DispatchService.delete_dispatch(dispatch_id)
    if not ok:
        return jsonify({"status": "error", "message": message}), 404
    return jsonify({"status": "okay", "message": message})

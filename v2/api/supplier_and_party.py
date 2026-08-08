from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.supplier_and_party import ALLOWED_CITIES, CommissionRate, Party

supplier_bp = Blueprint("supplier", __name__, url_prefix="/api/supplier")

@supplier_bp.route("/cities", methods=["GET"])
def get_supplier_cities():
    """
    Retrieve the list of allowed cities for suppliers.
    """
    return jsonify(ALLOWED_CITIES)


@supplier_bp.route("/<int:supplier_id>/commission-rates", methods=["GET"])
@jwt_required()
def get_commission_rates(supplier_id: int):
    """List a supplier's per-party commission rate overrides (parties without a row use the 2% default)."""
    rows = (
        db.session.query(CommissionRate, Party.name)
        .join(Party, CommissionRate.party_id == Party.id)
        .filter(CommissionRate.supplier_id == supplier_id)
        .order_by(Party.name)
        .all()
    )
    return jsonify([
        {
            "id": rate.id,
            "party_id": rate.party_id,
            "party_name": party_name,
            "rate_percent": float(rate.rate_percent),
        }
        for rate, party_name in rows
    ])


@supplier_bp.route("/<int:supplier_id>/commission-rates", methods=["POST"])
@jwt_required()
def upsert_commission_rate(supplier_id: int):
    """Create or update the commission rate for a supplier+party pair. Applies to new memos only."""
    data = request.json or {}
    party_id = data.get("party_id")
    rate_percent = data.get("rate_percent")
    if party_id is None or rate_percent is None:
        return jsonify({"status": "error", "message": "party_id and rate_percent are required"}), 400
    try:
        rate_percent = float(rate_percent)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "rate_percent must be a number"}), 400
    if not 0 <= rate_percent <= 100:
        return jsonify({"status": "error", "message": "rate_percent must be between 0 and 100"}), 400

    rate = CommissionRate.query.filter_by(supplier_id=supplier_id, party_id=int(party_id)).first()
    if rate:
        rate.rate_percent = rate_percent
    else:
        rate = CommissionRate(supplier_id=supplier_id, party_id=int(party_id), rate_percent=rate_percent)
        db.session.add(rate)
    db.session.commit()
    return jsonify({"status": "okay", "id": rate.id, "party_id": rate.party_id, "rate_percent": rate_percent})


@supplier_bp.route("/<int:supplier_id>/commission-rates/<int:party_id>", methods=["DELETE"])
@jwt_required()
def delete_commission_rate(supplier_id: int, party_id: int):
    """Remove a pair override so the pair falls back to the 2% default."""
    rate = CommissionRate.query.filter_by(supplier_id=supplier_id, party_id=party_id).first()
    if not rate:
        return jsonify({"status": "error", "message": "No commission rate found for this supplier and party"}), 404
    db.session.delete(rate)
    db.session.commit()
    return jsonify({"status": "okay"})

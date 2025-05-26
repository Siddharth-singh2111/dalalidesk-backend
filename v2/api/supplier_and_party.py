from flask import Blueprint, jsonify
from ..models.supplier_and_party import ALLOWED_CITIES

supplier_bp = Blueprint("supplier", __name__, url_prefix="/api/supplier")

@supplier_bp.route("/cities", methods=["GET"])
def get_supplier_cities():
    """
    Retrieve the list of allowed cities for suppliers.
    """
    return jsonify(ALLOWED_CITIES)

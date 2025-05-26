"""
API endpoints for dashboard metrics
"""
from flask import Blueprint, request, jsonify
from sqlalchemy import func, extract, not_, exists
from ..models.register import RegisterEntry
from ..models.memo import MemoEntry
from ..models.dalali import DalaliBills, DalaliEntry
from ..models.supplier_and_party import Supplier
from ..extensions import db
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/metrics', methods=['GET'])
def get_dashboard_metrics():
    """
    Get dashboard metrics with optional filtering by suppliers, parties, financial year, and city.
    
    Query Parameters:
        supplier_ids (str, optional): Comma-separated list of supplier IDs
        party_ids (str, optional): Comma-separated list of party IDs
        financial_year (str, optional): Filter by financial year (e.g., "2023-2024")
        city (str, optional): Filter by city
    
    Returns:
        JSON object with the following metrics:
        - total_register_amount: Total amount in register entries
        - pending_register_amount: Total amount of register entries with status N
        - total_commission: Total amount of commission earned
        - pending_commission: Total amount of commission left to collect (pending memos)
    """
    # Get filter parameters
    supplier_ids_param = request.args.get('supplier_ids', request.args.get('supplier_id', ''))
    party_ids_param = request.args.get('party_ids', request.args.get('party_id', ''))
    financial_year = request.args.get('financial_year', type=str)
    city = request.args.get('city', request.args.get('supplier_city', ''))
    
    # Parse comma-separated lists of IDs
    supplier_ids = []
    party_ids = []
    
    if supplier_ids_param:
        try:
            if ',' in supplier_ids_param:
                supplier_ids = [int(s.strip()) for s in supplier_ids_param.split(',') if s.strip().isdigit()]
            elif supplier_ids_param.strip().isdigit():
                supplier_ids = [int(supplier_ids_param)]
        except (ValueError, TypeError):
            pass
    
    if party_ids_param:
        try:
            if ',' in party_ids_param:
                party_ids = [int(p.strip()) for p in party_ids_param.split(',') if p.strip().isdigit()]
            elif party_ids_param.strip().isdigit():
                party_ids = [int(party_ids_param)]
        except (ValueError, TypeError):
            pass
    
    # Base filters
    register_filters = []
    memo_filters = []
    
    if supplier_ids:
        register_filters.append(RegisterEntry.supplier_id.in_(supplier_ids))
        memo_filters.append(MemoEntry.supplier_id.in_(supplier_ids))
    
    if party_ids:
        register_filters.append(RegisterEntry.party_id.in_(party_ids))
        memo_filters.append(MemoEntry.party_id.in_(party_ids))
    
    # Financial year filter
    if financial_year:
        try:
            start_year, end_year = map(int, financial_year.split('-'))
            if start_year >= end_year:
                raise ValueError("Start year must be less than end year for a financial year.")
            
            # Financial year starts on April 1st of start_year and ends on March 31st of end_year
            start_date = datetime(start_year, 4, 1)
            end_date = datetime(end_year, 3, 31, 23, 59, 59)
            
            register_filters.append(RegisterEntry.register_date >= start_date)
            register_filters.append(RegisterEntry.register_date <= end_date)
            memo_filters.append(MemoEntry.register_date >= start_date)
            memo_filters.append(MemoEntry.register_date <= end_date)
        except ValueError as e:
            return jsonify({"error": f"Invalid financial_year format or value: {str(e)}. Please use YYYY-YYYY format (e.g., 2023-2024)."}), 400

    # City filter
    if city:
        # We need to join RegisterEntry with Supplier to filter by city
        # And MemoEntry with Supplier to filter by city
        register_filters.append(RegisterEntry.supplier.has(Supplier.city == city))
        memo_filters.append(MemoEntry.supplier.has(Supplier.city == city))
    
    # 1. Total amount in register entries
    total_register_amount_query = db.session.query(func.sum(RegisterEntry.amount))
    if city: # Apply join only if city is present
        total_register_amount_query = total_register_amount_query.join(Supplier, RegisterEntry.supplier_id == Supplier.id)
    total_register_amount = total_register_amount_query.filter(*register_filters).scalar() or 0
    
    # 2. Total amount of register entries with status N
    pending_register_amount_query = db.session.query(func.sum(RegisterEntry.amount))
    if city: # Apply join only if city is present
        pending_register_amount_query = pending_register_amount_query.join(Supplier, RegisterEntry.supplier_id == Supplier.id)
    pending_register_amount = pending_register_amount_query.filter(RegisterEntry.status == 'N', *register_filters).scalar() or 0
    
    # 3. Total amount of commission earned
    total_commission_query = db.session.query(func.sum(MemoEntry.commision))
    if city: # Apply join only if city is present
        total_commission_query = total_commission_query.join(Supplier, MemoEntry.supplier_id == Supplier.id)
    total_commission = total_commission_query.filter(*memo_filters).scalar() or 0
    
    # 4. Total amount of commission left to collect
    # Define the subquery for pending memos (memos with no associated non-cancelled dalali entries)
    # This uses the same logic as MemoService.get_pending_memos but executes it in a single query
    pending_dalali_subquery = exists().where(
        DalaliBills.memo_id == MemoEntry.id,
        DalaliBills.dalali_entry.has(DalaliEntry.status != 'cancelled')
    )
    
    # Build the base query
    pending_commission_query = db.session.query(func.sum(MemoEntry.commision))
    pending_commission_query = pending_commission_query.filter(
        MemoEntry.commision != None,
        MemoEntry.less_gst_percentage != None,
        not_(pending_dalali_subquery)
    )
    
    # Apply filters
    if supplier_ids:
        pending_commission_query = pending_commission_query.filter(MemoEntry.supplier_id.in_(supplier_ids))
    
    if party_ids:
        pending_commission_query = pending_commission_query.filter(MemoEntry.party_id.in_(party_ids))
    
    if city:
        pending_commission_query = pending_commission_query.join(Supplier, MemoEntry.supplier_id == Supplier.id)
        pending_commission_query = pending_commission_query.filter(Supplier.city == city)
    
    # Apply financial year filter if provided
    if financial_year and start_date and end_date:
        pending_commission_query = pending_commission_query.filter(
            MemoEntry.register_date >= start_date,
            MemoEntry.register_date <= end_date
        )
    
    # Execute the query to get the total pending commission
    pending_commission = pending_commission_query.scalar() or 0
    
    return jsonify({
        "total_register_amount": total_register_amount,
        "pending_register_amount": pending_register_amount,
        "total_commission": total_commission,
        "pending_commission": pending_commission
    })

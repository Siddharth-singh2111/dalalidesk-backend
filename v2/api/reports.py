"""
API endpoints for report generation
"""
from datetime import datetime
from typing import Optional
import traceback
from flask import Blueprint, request, Response, jsonify, current_app, send_file
from marshmallow import ValidationError

from ..reports.dalali_memo_report import DalaliMemoReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@reports_bp.route('/dalali-memo', methods=['GET'])
def generate_dalali_memo_report():
    """
    Generate and download Dalali-Memo Excel report.
    
    Query Parameters:
        financial_year (str, optional): Financial year filter (e.g., "2024-2025")
        supplier_id (int, optional): Filter by supplier ID
        party_id (int, optional): Filter by party ID
        status (str, optional): Filter by status (Approved, Pending, Cancelled)
        from_date (str, optional): Filter by date range start (YYYY-MM-DD)
        to_date (str, optional): Filter by date range end (YYYY-MM-DD)
    
    Returns:
        Excel file as attachment
    """
    try:
        # Parse query parameters
        filters = {}
        
        if 'financial_year' in request.args:
            filters['financial_year'] = request.args.get('financial_year')
            
        if 'supplier_id' in request.args and request.args.get('supplier_id'):
            try:
                filters['supplier_id'] = int(request.args.get('supplier_id'))
            except ValueError:
                return jsonify({"error": "supplier_id must be an integer"}), 400
            
        if 'party_id' in request.args and request.args.get('party_id'):
            try:
                filters['party_id'] = int(request.args.get('party_id'))
            except ValueError:
                return jsonify({"error": "party_id must be an integer"}), 400
            
        if 'status' in request.args:
            status = request.args.get('status')
            valid_statuses = ['Approved', 'Pending', 'Cancelled']
            if status not in valid_statuses:
                return jsonify({"error": f"status must be one of: {', '.join(valid_statuses)}"}), 400
            filters['status'] = status
            
        if 'from_date' in request.args and request.args.get('from_date'):
            try:
                filters['from_date'] = datetime.strptime(request.args.get('from_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "from_date must be in YYYY-MM-DD format"}), 400
            
        if 'to_date' in request.args and request.args.get('to_date'):
            try:
                filters['to_date'] = datetime.strptime(request.args.get('to_date'), '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "to_date must be in YYYY-MM-DD format"}), 400
        
        # Generate the report
        report_service = DalaliMemoReportService()
        excel_file = report_service.generate_report(filters=filters)
        
        # Return as file download
        filename = f"Dalali_Memo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            excel_file, 
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
        
    except ValidationError as e:
        current_app.logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        # Get stack trace for detailed debugging
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error generating report: {str(e)}\n{stack_trace}")
        
        # Return a more detailed error for debugging
        if current_app.debug:
            return jsonify({
                "error": "Failed to generate report", 
                "details": str(e),
                "stack_trace": stack_trace
            }), 500
        else:
            # In production, don't expose implementation details
            return jsonify({"error": "Failed to generate report"}), 500

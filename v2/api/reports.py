"""
API endpoints for report generation
"""
from datetime import datetime
from typing import Optional
import traceback
from flask import Blueprint, request, Response, jsonify, current_app, send_file
from marshmallow import ValidationError

from ..reports.dalali_memo_report import DalaliMemoReportService
from ..reports.pending_payment_report import PendingPaymentReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@reports_bp.route('/local-dispatch', methods=['GET'])
def generate_local_dispatch_excel():
    """
    Local Dispatch Summary as an Excel download (flat, one row per dispatched bill).

    Query Parameters (all optional):
        from, to     : dispatch-date range (YYYY-MM-DD)
        party_ids    : comma-separated party ids
        transport    : substring match on transport name
    """
    import pandas as pd
    from psql import execute_query
    from API_Database import parse_date, sql_date
    from ..reports.utils import generate_excel_file

    try:
        start = request.args.get('from') or '2000-01-01'
        end = request.args.get('to') or '2100-12-31'
        start = sql_date(parse_date(start))
        end = sql_date(parse_date(end))

        clauses = [f"d.dispatch_date >= '{start}'", f"d.dispatch_date <= '{end}'"]
        party_ids = request.args.get('party_ids')
        if party_ids:
            ids = ','.join(str(int(x)) for x in party_ids.split(',') if x.strip())
            if ids:
                clauses.append(f"d.party_id IN ({ids})")
        transport = request.args.get('transport')
        if transport:
            safe = transport.replace("'", "''")
            clauses.append(f"db.transport_name ILIKE '%{safe}%'")

        where = ' AND '.join(clauses)
        query = f"""
            SELECT db.bill_number AS "Bill No",
                   db.bill_date AS "Bill Date",
                   p.name AS "Party Name",
                   s.name AS "Supplier",
                   db.lr_number AS "L.R. No.",
                   db.transport_name AS "Transport",
                   cnt.bills_in_dispatch AS "No. of Bills",
                   d.dispatch_date AS "Dispatch Date",
                   COALESCE(u.full_name, '-') AS "User"
            FROM dispatch_bill db
            JOIN dispatch d ON db.dispatch_id = d.id
            LEFT JOIN party p ON d.party_id = p.id
            LEFT JOIN supplier s ON db.supplier_id = s.id
            LEFT JOIN users u ON d.created_by = u.id
            JOIN (SELECT dispatch_id, COUNT(*) AS bills_in_dispatch
                  FROM dispatch_bill GROUP BY dispatch_id) cnt
                  ON cnt.dispatch_id = d.id
            WHERE {where}
            ORDER BY d.dispatch_date, d.serial_number NULLS LAST, d.id, db.bill_number
        """
        rows = execute_query(query)['result']
        df = pd.DataFrame(rows, columns=[
            "Bill No", "Bill Date", "Party Name", "Supplier", "L.R. No.",
            "Transport", "No. of Bills", "Dispatch Date", "User",
        ])
        excel_file = generate_excel_file(df, sheet_name="Local Dispatch")
        filename = f"Local_Dispatch_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            excel_file,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error generating local dispatch excel: {str(e)}\n{stack_trace}")
        if current_app.debug:
            return jsonify({"error": "Failed to generate local dispatch excel",
                            "details": str(e), "stack_trace": stack_trace}), 500
        return jsonify({"error": "Failed to generate local dispatch excel"}), 500


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


@reports_bp.route('/pending-payment', methods=['GET'])
def generate_pending_payment_report():
    """
    Generate and download Pending Payment Excel report with aging analysis.
    
    Query Parameters:
        financial_year (str, optional): Financial year filter (e.g., "2024-2025" or "2023-2024,2024-2025")
        supplier_id (int, optional): Filter by supplier ID
        party_id (int, optional): Filter by party ID
        from_date (str, optional): Filter by date range start (YYYY-MM-DD)
        to_date (str, optional): Filter by date range end (YYYY-MM-DD)
    
    Returns:
        Excel file as attachment with pending payment aging analysis
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
        report_service = PendingPaymentReportService()
        excel_file = report_service.generate_report(filters=filters)
        
        # Return as file download
        filename = f"Pending_Payment_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
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
        current_app.logger.error(f"Error generating pending payment report: {str(e)}\n{stack_trace}")
        
        # Return a more detailed error for debugging
        if current_app.debug:
            return jsonify({
                "error": "Failed to generate pending payment report", 
                "details": str(e),
                "stack_trace": stack_trace
            }), 500
        else:
            # In production, don't expose implementation details
            return jsonify({"error": "Failed to generate pending payment report"}), 500

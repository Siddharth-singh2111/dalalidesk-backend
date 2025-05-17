"""
Dalali-Memo Report Generation Service

This module provides functionality to generate Excel reports that combine
data from Dalali Entries and Memo Entries.
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import pandas as pd
from sqlalchemy import func, and_, or_, desc, outerjoin
from sqlalchemy.orm import aliased, joinedload

from ..extensions import db
from ..models.dalali import (
    DalaliEntry, DalaliBills, DalaliReceiverPayments, 
    DalaliSenderPayments, TdsDetails, PartDalali
)
from ..models.memo import MemoEntry
from ..models.supplier_and_party import Supplier, Party
from ..schemas.dalali import DalaliEntrySchema, DalaliBillSchema, DalaliReceiverPaymentSchema, PartDalaliSchema
from ..schemas.memo import MemoEntrySchema
from .utils import calculate_financial_year, generate_excel_file


class DalaliMemoReportService:
    """
    Service class for generating Dalali-Memo reports in Excel format.
    Combines data from DalaliEntry and MemoEntry tables and related entities.
    """

    def __init__(self):
        """Initialize the report service."""
        pass

    def _build_memo_query(
        self, 
        financial_year: Optional[str] = None,
        supplier_id: Optional[int] = None,
        party_id: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ):
        """
        Build the database query to retrieve Memo information with optional Dalali associations.
        This includes memos with valid commission even if they have no associated dalali entries.
        
        Args:
            financial_year: Optional financial year filter (e.g., "2024-2025")
            supplier_id: Optional supplier ID filter
            party_id: Optional party ID filter
            status: Optional status filter (Approved, Pending, Cancelled)
            from_date: Optional date range start
            to_date: Optional date range end
            
        Returns:
            SQLAlchemy query object with all joins applied
        """
        # Start query with MemoEntry and use left joins to optionally include dalali data
        query = (
            db.session.query(
                MemoEntry,
                Supplier,
                Party,
                DalaliBills,
                DalaliEntry
            )
            .join(Supplier, MemoEntry.supplier_id == Supplier.id)
            .join(Party, MemoEntry.party_id == Party.id)
            .outerjoin(DalaliBills, MemoEntry.id == DalaliBills.memo_id)
            .outerjoin(DalaliEntry, DalaliBills.dalali_id == DalaliEntry.id)
            .options(
                joinedload(DalaliEntry.dalali_receiver_payments),
                joinedload(DalaliEntry.tds_details)
            )
            # Include memos with valid commission or those with dalali entries
            .filter(or_(
                and_(MemoEntry.commision != None, MemoEntry.less_gst_percentage != None),
                DalaliEntry.id != None
            ))
        )
        
        # Apply filters
        if financial_year:
            # Parse the financial year string
            start_year, end_year = map(int, financial_year.split('-'))
            
            # Create date range for the financial year (April 1st to March 31st)
            fy_start_date = datetime(start_year, 4, 1)
            fy_end_date = datetime(end_year, 3, 31)
            
            query = query.filter(
                MemoEntry.register_date.between(fy_start_date, fy_end_date)
            )
            
        if supplier_id:
            # Apply supplier filter to either memo or dalali
            query = query.filter(or_(
                MemoEntry.supplier_id == supplier_id,
                DalaliEntry.supplier_id == supplier_id
            ))
            
        if party_id:
            query = query.filter(MemoEntry.party_id == party_id)
            
        if status:
            # Only apply status filter to records with dalali entries
            query = query.filter(or_(
                DalaliEntry.id == None,  # Don't filter memos without dalali
                DalaliEntry.status == status
            ))
            
        if from_date:
            # Apply date filters to memo date
            query = query.filter(MemoEntry.register_date >= from_date)
            
        if to_date:
            query = query.filter(MemoEntry.register_date <= to_date)
            
        return query
        
    def _build_part_dalali_query(
        self, 
        supplier_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ):
        """
        Build the database query to retrieve Part Dalali entries that have no associations.
        
        Args:
            supplier_id: Optional supplier ID filter
            from_date: Optional date range start
            to_date: Optional date range end
            
        Returns:
            SQLAlchemy query object for part dalali entries
        """
        query = (
            db.session.query(
                PartDalali,
                Supplier,
                DalaliEntry
            )
            .join(Supplier, PartDalali.supplier_id == Supplier.id)
            .join(DalaliEntry, PartDalali.dalali_id == DalaliEntry.id)
            .filter(PartDalali.used == False)  # Only include unused part dalali entries
        )
        
        if supplier_id:
            query = query.filter(PartDalali.supplier_id == supplier_id)
            
        if from_date:
            query = query.filter(DalaliEntry.register_date >= from_date)
            
        if to_date:
            query = query.filter(DalaliEntry.register_date <= to_date)
            
        return query
    
    def _build_query(
        self, 
        financial_year: Optional[str] = None,
        supplier_id: Optional[int] = None,
        party_id: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ):
        """
        Build the database queries to retrieve all required information.
        
        Args:
            financial_year: Optional financial year filter (e.g., "2024-2025")
            supplier_id: Optional supplier ID filter
            party_id: Optional party ID filter
            status: Optional status filter (Approved, Pending, Cancelled)
            from_date: Optional date range start
            to_date: Optional date range end
            
        Returns:
            Tuple of SQLAlchemy query objects (memo_query, part_dalali_query)
        """
        # Build separate queries for memo entries and part dalali entries
        memo_query = self._build_memo_query(
            financial_year=financial_year,
            supplier_id=supplier_id,
            party_id=party_id,
            status=status,
            from_date=from_date,
            to_date=to_date
        )
        
        part_dalali_query = self._build_part_dalali_query(
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date
        )
        
        return memo_query, part_dalali_query
    
    def _format_memo_data(self, memo_results) -> List[Dict[str, Any]]:
        """
        Transform the memo query results into the format needed for the report.
        This handles both memos with and without dalali entries.
        
        Args:
            memo_results: Results from the memo query
            
        Returns:
            List of dictionaries with formatted data for the report
        """
        formatted_data = []
        
        for i, (memo, supplier, party, dalali_bill, dalali) in enumerate(memo_results, start=1):
            try:
                # Convert SQLAlchemy models to Pydantic models for proper datetime handling
                memo_schema = MemoEntrySchema.model_validate(memo)
                
                # Calculate financial year from memo date
                financial_year = calculate_financial_year(memo.register_date)
                
                # Calculate net amount after GST
                net_amount = memo.amount
                if memo.less_gst is not None:
                    net_amount -= memo.less_gst
                
                # Base row data with memo information
                row_data = {
                    "S.NO.": i,
                    "FINANCIAL YEAR": financial_year,
                    "SUPPLIER": supplier.name if supplier else None,
                    "PARTY": party.name if party else None,
                    "CITY": supplier.city if supplier else None,
                    "MEMO NO.": memo.memo_number,
                    "MEMO DATE": memo.register_date,
                    "DD AMOUNT": memo.amount,
                    "LESS GST %": memo.less_gst_percentage,
                    "LESS GST": memo.less_gst,
                    "NET AMOUNT": net_amount,
                    "2%": memo.commision,
                    
                    # Initialize dalali fields as empty/None
                    "DALALI NO.": None,
                    "DALALI ENTRY DATE": None,
                    "PAID AMOUNT": None,
                    "TDS DEDUCTION": None,
                    "OTHER DEDUCTION": None,
                    "STATUS": "No Dalali",  # Default status for memos without dalali
                    "APPROVAL DATE": None,
                    "NOTES": None,
                    "TALLY BILL NO.": None,
                    "FIRM NAME": None,
                    "FIRM ACCOUNT NAME": None
                }
                
                # If there's an associated dalali entry, add its information
                if dalali is not None:
                    dalali_schema = DalaliEntrySchema.model_validate(dalali)
                    
                    # Get the first receiver payment (if any)
                    receiver_payment = None
                    if dalali.dalali_receiver_payments:
                        db_receiver = dalali.dalali_receiver_payments[0]
                        receiver_payment = DalaliReceiverPaymentSchema.model_validate(db_receiver)
                    
                    # Update row with dalali information
                    row_data.update({
                        "DALALI NO.": dalali.dalali_number,
                        "DALALI ENTRY DATE": dalali.register_date,
                        "PAID AMOUNT": dalali.amount,
                        "TDS DEDUCTION": dalali.tds_deduction,
                        "OTHER DEDUCTION": dalali.other_deduction,
                        "STATUS": dalali.status,
                        "APPROVAL DATE": db_receiver.received_date if receiver_payment else None,
                        "NOTES": dalali.notes,
                        "TALLY BILL NO.": dalali.tally_bill_no,
                        "FIRM NAME": (db_receiver.firm_name if receiver_payment else None),
                        "FIRM ACCOUNT NAME": (db_receiver.firm_bank_name if receiver_payment else None)
                    })
                
                formatted_data.append(row_data)
                
            except Exception as e:
                # Log the error but continue processing other records
                print(f"Error processing memo record: {e}")
                continue
            
        return formatted_data
    
    def _format_part_dalali_data(self, part_dalali_results, start_index: int) -> List[Dict[str, Any]]:
        """
        Transform the part dalali query results into the format needed for the report.
        
        Args:
            part_dalali_results: Results from the part dalali query
            start_index: Starting index for S.NO. field (continuing from memo data)
            
        Returns:
            List of dictionaries with formatted data for the report
        """
        formatted_data = []
        
        for i, (part_dalali, supplier, original_dalali) in enumerate(part_dalali_results, start=start_index):
            try:
                # Calculate financial year from original dalali date
                financial_year = calculate_financial_year(original_dalali.register_date)
                
                # Format the row data for a part dalali entry
                row_data = {
                    "S.NO.": i,
                    "FINANCIAL YEAR": financial_year,
                    "SUPPLIER": supplier.name if supplier else None,
                    "PARTY": "N/A - Part Dalali",  # Indicate this is a part dalali record
                    "CITY": supplier.city if supplier else None,
                    "MEMO NO.": None,  # No associated memo
                    "MEMO DATE": None,
                    "DD AMOUNT": None,
                    "LESS GST %": None,
                    "LESS GST": None,
                    "NET AMOUNT": None,
                    "2%": None,
                    "DALALI NO.": original_dalali.dalali_number,
                    "DALALI ENTRY DATE": original_dalali.register_date,
                    "PAID AMOUNT": part_dalali.dalali_amount,
                    "TDS DEDUCTION": None,
                    "OTHER DEDUCTION": None,
                    "STATUS": "Part Dalali (Unused)",
                    "APPROVAL DATE": None,
                    "NOTES": "Part dalali entry without association",
                    "TALLY BILL NO.": None,
                    "FIRM NAME": None,
                    "FIRM ACCOUNT NAME": None
                }
                
                formatted_data.append(row_data)
                
            except Exception as e:
                # Log the error but continue processing other records
                print(f"Error processing part dalali record: {e}")
                continue
            
        return formatted_data
    
    def _format_report_data(self, memo_results, part_dalali_results) -> List[Dict[str, Any]]:
        """
        Transform all query results into the format needed for the report.
        
        Args:
            memo_results: Results from the memo query
            part_dalali_results: Results from the part dalali query
            
        Returns:
            List of dictionaries with formatted data for the report
        """
        # Format memo data (including those with associated dalali entries)
        memo_data = self._format_memo_data(memo_results)
        
        # Format part dalali data, continuing the index numbering
        part_dalali_data = self._format_part_dalali_data(
            part_dalali_results, 
            start_index=len(memo_data) + 1
        )
        
        # Combine both datasets
        return memo_data + part_dalali_data
    
    def generate_report(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        sheet_name: str = "Dalali Memo Report"
    ):
        """
        Generate the Dalali-Memo Excel report.
        
        Args:
            filters: Optional dictionary of filters to apply to the report
            sheet_name: Name for the Excel sheet
            
        Returns:
            BytesIO object containing the Excel file
        """
        filters = filters or {}
        
        # Build and execute both queries
        memo_query, part_dalali_query = self._build_query(
            financial_year=filters.get('financial_year'),
            supplier_id=filters.get('supplier_id'),
            party_id=filters.get('party_id'),
            status=filters.get('status'),
            from_date=filters.get('from_date'),
            to_date=filters.get('to_date')
        )
        
        memo_results = memo_query.all()
        part_dalali_results = part_dalali_query.all()
        
        # Format the data for the report
        formatted_data = self._format_report_data(memo_results, part_dalali_results)
        
        # Convert to DataFrame
        df = pd.DataFrame(formatted_data)
        
        # Generate Excel file
        excel_file = generate_excel_file(df, sheet_name=sheet_name)
        
        return excel_file

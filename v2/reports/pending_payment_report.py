"""
Pending Payment Report Generation Service

This module provides functionality to generate Excel reports that analyze
pending payments based on register entries with status 'N' (unpaid).
Includes aging analysis (>120 days, 60-120 days, <60 days).
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import func, and_, or_, desc, case
from sqlalchemy.orm import aliased, joinedload

from ..extensions import db
from ..models.register import RegisterEntry
from ..models.supplier_and_party import Supplier, Party
from ..models.memo import MemoEntry, PartPayments
from .utils import calculate_financial_year, generate_excel_file, generate_multi_sheet_excel_file


class PendingPaymentReportService:
    """
    Service class for generating Pending Payment reports in Excel format.
    Analyzes pending payments from register entries with status 'N' (unpaid).
    Groups by financial year and party with aging buckets.
    
    The report includes:
    - Aging analysis of pending payments (>120 days, 60-120 days, <60 days)
    - Available part payments (unused) from suppliers in the same city
    - Actual pending amounts after considering available part payments
    """

    def __init__(self):
        """Initialize the report service."""
        pass

    def _calculate_aging_days(self, entry_date: datetime) -> int:
        """
        Calculate the number of days between entry date and today.
        
        Args:
            entry_date: The date of the entry
            
        Returns:
            Number of days since the entry
        """
        if not entry_date:
            return 0
        return (datetime.now().date() - entry_date.date()).days

    def _get_aging_bucket(self, days: int) -> str:
        """
        Determine the aging bucket based on number of days.
        
        Args:
            days: Number of days since entry
            
        Returns:
            Aging bucket string
        """
        if days > 120:
            return ">120 days"
        elif days >= 60:
            return "60-120 days"
        else:
            return "<60 days"

    def _build_pending_payment_query(
        self, 
        financial_year: Optional[Union[str, List[str]]] = None,
        supplier_id: Optional[int] = None,
        party_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ):
        """
        Build the database query to retrieve pending payment information from register entries.
        This includes register entries with status 'N' (unpaid) that have remaining amounts.
        
        Args:
            financial_year: Optional financial year filter - can be a single year (e.g., "2024-2025") 
                           or a list of years (e.g., ["2023-2024", "2024-2025"])
            supplier_id: Optional supplier ID filter
            party_id: Optional party ID filter
            from_date: Optional date range start
            to_date: Optional date range end
            
        Returns:
            SQLAlchemy query object with all joins applied
        """
        # Main query to get register entries with pending payments
        query = (
            db.session.query(
                RegisterEntry,
                Supplier,
                Party
            )
            .join(Supplier, RegisterEntry.supplier_id == Supplier.id)
            .join(Party, RegisterEntry.party_id == Party.id)
            .filter(RegisterEntry.status == 'N')  # Only unpaid entries
            .filter(
                # Only entries with remaining amounts (amount - gr_amount - deduction - partial_amount > 0)
                (RegisterEntry.amount - RegisterEntry.gr_amount - 
                 RegisterEntry.deduction - RegisterEntry.partial_amount) > 0
            )
        )
        
        # Apply filters
        if financial_year:
            # Handle both single financial year (str) and multiple financial years (list)
            financial_years = financial_year.split(',') if isinstance(financial_year, str) else financial_year
            
            # Create date range conditions for each financial year
            financial_year_conditions = []
            for fy in financial_years:
                # Parse the financial year string
                start_year, end_year = map(int, fy.split('-'))
                
                # Create date range for this financial year (April 1st to March 31st)
                fy_start_date = datetime(start_year, 4, 1)
                fy_end_date = datetime(end_year, 3, 31)
                
                # Add a condition for this financial year
                financial_year_conditions.append(
                    RegisterEntry.register_date.between(fy_start_date, fy_end_date)
                )
            
            # Apply the combined conditions with OR logic if we have any conditions
            if financial_year_conditions:
                query = query.filter(or_(*financial_year_conditions))
            
        if supplier_id:
            query = query.filter(RegisterEntry.supplier_id == supplier_id)
            
        if party_id:
            query = query.filter(RegisterEntry.party_id == party_id)
            
        if from_date:
            query = query.filter(RegisterEntry.register_date >= from_date)
            
        if to_date:
            query = query.filter(RegisterEntry.register_date <= to_date)
            
        return query

    def _get_available_part_payments_by_city(self, party_id: int, city: str) -> float:
        """
        Get the total available part payments for a party from suppliers in a specific city.
        
        Args:
            party_id: The party ID
            city: The city to filter suppliers by
            
        Returns:
            Total available part payment amount from suppliers in the specified city
        """
        # Query for unused part payments for this party from suppliers in the specified city
        part_payments_query = (
            db.session.query(func.sum(MemoEntry.amount))
            .join(PartPayments, PartPayments.memo_id == MemoEntry.id)
            .join(Supplier, PartPayments.supplier_id == Supplier.id)
            .filter(
                PartPayments.party_id == party_id,
                PartPayments.used == False,
                Supplier.city == city
            )
        ).scalar()
        
        return part_payments_query or 0

    def _get_available_part_payments_all_cities(self, party_id: int) -> float:
        """
        Get the total available part payments for a party from suppliers across all cities.
        
        Args:
            party_id: The party ID
            
        Returns:
            Total available part payment amount from all suppliers regardless of city
        """
        # Query for unused part payments for this party from all suppliers
        part_payments_query = (
            db.session.query(func.sum(MemoEntry.amount))
            .join(PartPayments, PartPayments.memo_id == MemoEntry.id)
            .filter(
                PartPayments.party_id == party_id,
                PartPayments.used == False
            )
        ).scalar()
        
        return part_payments_query or 0

    def _format_pending_payment_data(self, results, group_by_financial_year: bool = True) -> List[Dict[str, Any]]:
        """
        Transform the query results into the format needed for the pending payment report.
        
        Args:
            results: Results from the pending payment query (RegisterEntry, Supplier, Party)
            group_by_financial_year: Whether to group by financial year or show all years together
            
        Returns:
            List of dictionaries with formatted data for the report
        """
        # Group data by party and optionally by financial year
        grouped_data = {}
        
        for register_entry, supplier, party in results:
            # Calculate financial year from register date
            financial_year = calculate_financial_year(register_entry.register_date)
            
            # Create grouping key
            if group_by_financial_year:
                group_key = (financial_year, party.id, party.name, supplier.city if supplier else None)
            else:
                group_key = ("All Years", party.id, party.name, supplier.city if supplier else None)
            
            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    'financial_year': group_key[0],
                    'party_id': group_key[1],
                    'party_name': group_key[2],
                    'city': group_key[3],
                    'pending_amounts': {
                        '>120 days': 0,
                        '60-120 days': 0,
                        '<60 days': 0
                    },
                    'total_pending': 0
                }
            
            # Calculate pending amount from register entry
            # Pending = amount - gr_amount - deduction - partial_amount
            pending_amount = (
                register_entry.amount - 
                register_entry.gr_amount - 
                register_entry.deduction - 
                register_entry.partial_amount
            )
            
            if pending_amount > 0:
                # Calculate aging based on register date
                aging_days = self._calculate_aging_days(register_entry.register_date)
                aging_bucket = self._get_aging_bucket(aging_days)
                
                # Add to appropriate bucket
                grouped_data[group_key]['pending_amounts'][aging_bucket] += pending_amount
                grouped_data[group_key]['total_pending'] += pending_amount

        # Convert grouped data to list format and calculate part payments
        formatted_data = []
        for i, ((fy, party_id, party_name, city), data) in enumerate(grouped_data.items(), start=1):
            # Get available part payments for this party from suppliers in this city
            available_part_payments = self._get_available_part_payments_by_city(party_id, city) if city else 0
            
            # Calculate actual pending amount (total pending - available part payments)
            actual_pending = max(0, data['total_pending'] - available_part_payments)
            
            row_data = {
                "S.NO.": i,
                "FINANCIAL YEAR": data['financial_year'],
                "PARTY NAME": data['party_name'],
                "CITY": data['city'],
                "PENDING PAYMENT >120 DAYS": data['pending_amounts']['>120 days'],
                "PENDING PAYMENT 60-120 DAYS": data['pending_amounts']['60-120 days'],
                "PENDING PAYMENT <60 DAYS": data['pending_amounts']['<60 days'],
                "TOTAL PENDING": data['total_pending'],
                "PART PAYMENT AVAILABLE": available_part_payments,
                "ACTUAL PENDING": actual_pending
            }
            formatted_data.append(row_data)
        
        # Sort by financial year and then by party name
        formatted_data.sort(key=lambda x: (x['FINANCIAL YEAR'], x['PARTY NAME']))
        
        # Renumber after sorting
        for i, row in enumerate(formatted_data, start=1):
            row["S.NO."] = i
            
        return formatted_data

    def _format_pending_payment_data_no_city(self, results, group_by_financial_year: bool = True) -> List[Dict[str, Any]]:
        """
        Transform the query results into the format needed for the pending payment report
        without city separation. Aggregates all data by party regardless of city.
        
        Args:
            results: Results from the pending payment query (RegisterEntry, Supplier, Party)
            group_by_financial_year: Whether to group by financial year or show all years together
            
        Returns:
            List of dictionaries with formatted data for the report (no city separation)
        """
        # Group data by party only (no city separation)
        grouped_data = {}
        
        for register_entry, supplier, party in results:
            # Calculate financial year from register date
            financial_year = calculate_financial_year(register_entry.register_date)
            
            # Create grouping key without city
            if group_by_financial_year:
                group_key = (financial_year, party.id, party.name)
            else:
                group_key = ("All Years", party.id, party.name)
            
            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    'financial_year': group_key[0],
                    'party_id': group_key[1],
                    'party_name': group_key[2],
                    'pending_amounts': {
                        '>120 days': 0,
                        '60-120 days': 0,
                        '<60 days': 0
                    },
                    'total_pending': 0
                }
            
            # Calculate pending amount from register entry
            # Pending = amount - gr_amount - deduction - partial_amount
            pending_amount = (
                register_entry.amount - 
                register_entry.gr_amount - 
                register_entry.deduction - 
                register_entry.partial_amount
            )
            
            if pending_amount > 0:
                # Calculate aging based on register date
                aging_days = self._calculate_aging_days(register_entry.register_date)
                aging_bucket = self._get_aging_bucket(aging_days)
                
                # Add to appropriate bucket
                grouped_data[group_key]['pending_amounts'][aging_bucket] += pending_amount
                grouped_data[group_key]['total_pending'] += pending_amount

        # Convert grouped data to list format and calculate part payments across all cities
        formatted_data = []
        for i, ((fy, party_id, party_name), data) in enumerate(grouped_data.items(), start=1):
            # Get available part payments for this party from all suppliers (all cities)
            available_part_payments = self._get_available_part_payments_all_cities(party_id)
            
            # Calculate actual pending amount (total pending - available part payments)
            actual_pending = max(0, data['total_pending'] - available_part_payments)
            
            row_data = {
                "S.NO.": i,
                "FINANCIAL YEAR": data['financial_year'],
                "PARTY NAME": data['party_name'],
                "PENDING PAYMENT >120 DAYS": data['pending_amounts']['>120 days'],
                "PENDING PAYMENT 60-120 DAYS": data['pending_amounts']['60-120 days'],
                "PENDING PAYMENT <60 DAYS": data['pending_amounts']['<60 days'],
                "TOTAL PENDING": data['total_pending'],
                "PART PAYMENT AVAILABLE": available_part_payments,
                "ACTUAL PENDING": actual_pending
            }
            formatted_data.append(row_data)
        
        # Sort by financial year and then by party name
        formatted_data.sort(key=lambda x: (x['FINANCIAL YEAR'], x['PARTY NAME']))
        
        # Renumber after sorting
        for i, row in enumerate(formatted_data, start=1):
            row["S.NO."] = i
            
        return formatted_data

    def _format_pending_payment_data_supplier_wise(self, results, group_by_financial_year: bool = True) -> List[Dict[str, Any]]:
        """
        Transform the query results into the format needed for the supplier-wise pending payment report.
        Groups data by party and supplier, showing individual supplier breakdowns.
        
        Args:
            results: Results from the pending payment query (RegisterEntry, Supplier, Party)
            group_by_financial_year: Whether to group by financial year or show all years together
            
        Returns:
            List of dictionaries with formatted data for the supplier-wise report
        """
        # Group data by party, supplier, and optionally by financial year
        grouped_data = {}
        
        for register_entry, supplier, party in results:
            # Calculate financial year from register date
            financial_year = calculate_financial_year(register_entry.register_date)
            
            # Create grouping key with supplier information
            if group_by_financial_year:
                group_key = (financial_year, party.id, party.name, supplier.id, supplier.name)
            else:
                group_key = ("All Years", party.id, party.name, supplier.id, supplier.name)
            
            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    'financial_year': group_key[0],
                    'party_id': group_key[1],
                    'party_name': group_key[2],
                    'supplier_id': group_key[3],
                    'supplier_name': group_key[4],
                    'pending_amounts': {
                        '>120 days': 0,
                        '60-120 days': 0,
                        '<60 days': 0
                    },
                    'total_pending': 0
                }
            
            # Calculate pending amount from register entry
            # Pending = amount - gr_amount - deduction - partial_amount
            pending_amount = (
                register_entry.amount - 
                register_entry.gr_amount - 
                register_entry.deduction - 
                register_entry.partial_amount
            )
            
            if pending_amount > 0:
                # Calculate aging based on register date
                aging_days = self._calculate_aging_days(register_entry.register_date)
                aging_bucket = self._get_aging_bucket(aging_days)
                
                # Add to appropriate bucket
                grouped_data[group_key]['pending_amounts'][aging_bucket] += pending_amount
                grouped_data[group_key]['total_pending'] += pending_amount

        # Convert grouped data to list format and calculate part payments for each supplier
        formatted_data = []
        for i, ((fy, party_id, party_name, supplier_id, supplier_name), data) in enumerate(grouped_data.items(), start=1):
            # Get available part payments for this party from this specific supplier
            available_part_payments = self._get_available_part_payments_by_supplier(party_id, supplier_id)
            
            # Calculate actual pending amount (total pending - available part payments from this supplier)
            actual_pending = max(0, data['total_pending'] - available_part_payments)
            
            row_data = {
                "S.NO.": i,
                "FINANCIAL YEAR": data['financial_year'],
                "PARTY NAME": data['party_name'],
                "SUPPLIER NAME": data['supplier_name'],
                "PENDING PAYMENT >120 DAYS": data['pending_amounts']['>120 days'],
                "PENDING PAYMENT 60-120 DAYS": data['pending_amounts']['60-120 days'],
                "PENDING PAYMENT <60 DAYS": data['pending_amounts']['<60 days'],
                "TOTAL PENDING": data['total_pending'],
                "PART PAYMENT AVAILABLE": available_part_payments,
                "ACTUAL PENDING": actual_pending
            }
            formatted_data.append(row_data)
        
        # Sort by financial year, party name, then supplier name
        formatted_data.sort(key=lambda x: (x['FINANCIAL YEAR'], x['PARTY NAME'], x['SUPPLIER NAME']))
        
        # Renumber after sorting
        for i, row in enumerate(formatted_data, start=1):
            row["S.NO."] = i
            
        return formatted_data

    def _get_available_part_payments_by_supplier(self, party_id: int, supplier_id: int) -> float:
        """
        Get the total available part payments for a party from a specific supplier.
        
        Args:
            party_id: The party ID
            supplier_id: The supplier ID
            
        Returns:
            Total available part payment amount from the specific supplier
        """
        # Query for unused part payments for this party from the specific supplier
        part_payments_query = (
            db.session.query(func.sum(MemoEntry.amount))
            .join(PartPayments, PartPayments.memo_id == MemoEntry.id)
            .filter(
                PartPayments.party_id == party_id,
                PartPayments.supplier_id == supplier_id,
                PartPayments.used == False
            )
        ).scalar()
        
        return part_payments_query or 0

    def generate_report(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        sheet_name: str = "Pending Payment Report"
    ):
        """
        Generate the Pending Payment Excel report based on register entries with status 'N'.
        Creates three sheets with different levels of detail.
        
        The report includes:
        - Aging analysis (>120 days, 60-120 days, <60 days)
        - Total pending amounts from register entries
        - Available part payments (unused) from suppliers
        - Actual pending amounts (total pending - available part payments)
        
        Sheet 1 (City-wise): Groups data by party and city, considers part payments from same city only
        Sheet 2 (Consolidated): Groups data by party only, considers part payments from all cities
        Sheet 3 (Supplier-wise): Groups data by party and supplier, shows individual supplier breakdowns
        
        Args:
            filters: Optional dictionary of filters to apply to the report
                     'financial_year' can be a single year (str) or multiple years (list)
            sheet_name: Base name for the Excel sheets (will be modified for each sheet)
            
        Returns:
            BytesIO object containing the Excel file with three sheets
        """
        filters = filters or {}
        
        # Determine if we should group by financial year
        financial_year_filter = filters.get('financial_year')
        group_by_financial_year = financial_year_filter is not None
        
        # Build and execute query
        query = self._build_pending_payment_query(
            financial_year=financial_year_filter,
            supplier_id=filters.get('supplier_id'),
            party_id=filters.get('party_id'),
            from_date=filters.get('from_date'),
            to_date=filters.get('to_date')
        )
        
        results = query.all()
        
        # Format the data for all three sheets
        # Sheet 1: With city separation
        formatted_data_with_city = self._format_pending_payment_data(results, group_by_financial_year)
        df_with_city = pd.DataFrame(formatted_data_with_city)
        
        # Sheet 2: Without city separation (consolidated)
        formatted_data_no_city = self._format_pending_payment_data_no_city(results, group_by_financial_year)
        df_no_city = pd.DataFrame(formatted_data_no_city)
        
        # Sheet 3: Supplier-wise breakdown
        formatted_data_supplier_wise = self._format_pending_payment_data_supplier_wise(results, group_by_financial_year)
        df_supplier_wise = pd.DataFrame(formatted_data_supplier_wise)
        
        # Prepare sheets data (Excel sheet names must be <= 31 characters)
        sheets_data = {
            "City-wise Report": df_with_city,
            "Consolidated Report": df_no_city,
            "Supplier-wise Report": df_supplier_wise
        }
        
        # Generate Excel file with multiple sheets
        excel_file = generate_multi_sheet_excel_file(sheets_data)
        
        return excel_file

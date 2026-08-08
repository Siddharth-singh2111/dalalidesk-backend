from __future__ import annotations
from typing import List, Dict, Optional
from psql import execute_query
from pypika import Query, Table, Field, Order, functions as fn
from Exceptions import DataError
import math
import sys
sys.path.append('../')

def get_commission_rate(supplier_id: int, party_id: int) -> float:
    """
    Get the commission rate (percent) for a supplier+party pair from commission_rates,
    falling back to the 2% default when no override exists (or the table is unreachable).
    """
    try:
        rates = Table('commission_rates')
        query = Query.from_(rates).select(rates.rate_percent)\
            .where((rates.supplier_id == supplier_id) & (rates.party_id == party_id))
        response = execute_query(query.get_sql())
        if response.get('status') == 'okay' and response['result']:
            return float(response['result'][0]['rate_percent'])
    except Exception:
        pass
    return 2.0

def calculate_commission(amount: float, gst_percentage: float = 4.762, rate_percent: float = 2.0) -> Dict[str, float]:
    """
    Calculate commission amount based on memo amount.
    
    This function first validates the inputs to ensure that:
      - Both the memo amount and GST percentage are numbers.
      - Both values are finite (i.e. not NaN or infinite).
      - Both values are non-negative.
    
    Then, it removes GST from the amount and calculates 2% of the remaining amount.
    
    Args:
        amount: The memo amount (must be a finite, non-negative number).
        gst_percentage: The GST percentage to remove (must be a finite, non-negative number; default: 4.762).
        
    Returns:
        A dictionary containing:
        - 'amount_without_gst': The memo amount with GST removed, rounded to 2 decimal places.
        - 'commission': The calculated commission amount rounded to 2 decimal places.
        
    Raises:
        DataError: If any of the input validations fail.
    """
    # Validate that the memo amount is a numeric, finite, and non-negative value.
    if not isinstance(amount, (int, float)) or not math.isfinite(amount):
        raise DataError("Invalid amount: must be a finite number.")
    if amount < 0:
        raise DataError("Invalid amount: memo amount cannot be negative.")
    
    # Validate that gst_percentage is a numeric, finite, and non-negative value.
    if not isinstance(gst_percentage, (int, float)) or not math.isfinite(gst_percentage):
        raise DataError("Invalid GST percentage: must be a finite number.")
    
    # If 5 or 12 change it to 4.762 or 10.7
    if gst_percentage == 5: # 5% GST
        gst_percentage = 4.762
    elif gst_percentage == 12: # 12% GST
        gst_percentage = 10.7

    if gst_percentage != 4.762 and gst_percentage != 10.7:
        raise DataError("Invalid GST percentage: must be 5% or 12%.")
    # Validate the commission rate (percent)
    if not isinstance(rate_percent, (int, float)) or not math.isfinite(rate_percent) or not 0 <= rate_percent <= 100:
        raise DataError("Invalid commission rate: must be a percentage between 0 and 100.")

    # Remove GST from amount
    amount_without_gst = amount - (amount * (gst_percentage / 100))
    amount_without_gst = math.ceil(amount_without_gst)

    # Commission on the amount after GST removal (default 2%, pair overrides via commission_rates)
    commission = amount_without_gst * (rate_percent / 100)
    commission = math.ceil(commission)
    
    return {
        'amount_without_gst': amount_without_gst,
        'commission': commission
    }

def get_memo_dalali_payment(memo_id: int) -> Optional[Dict]:
    """
    Get dalali payment information for a specific memo entry
    
    Args:
        memo_id: The ID of the memo entry
        
    Returns:
        Dictionary containing dalali payment information or None if not found
    """
    dalali_payments = Table('memo_dalali_payments')
    query = Query.from_(dalali_payments).select('*').where(dalali_payments.memo_id == memo_id)
    sql = query.get_sql()
    response = execute_query(sql)
    
    if len(response['result']) == 0:
        return None
    
    return response['result'][0]

def is_memo_used_by_dalali(memo_id: int) -> bool:
    """
    Check whether a memo entry is referenced by any dalali entry (dalali_bills table).
    """
    dalali_bills = Table('dalali_bills')
    query = Query.from_(dalali_bills).select(dalali_bills.id).where(dalali_bills.memo_id == memo_id)
    response = execute_query(query.get_sql())
    return len(response['result']) > 0

def get_all_memo_entries_with_dalali(start_date: str = None, end_date: str = None) -> List[Dict]:
    """
    Get all memo entries with dalali payment information, optionally filtered by date range
    
    Args:
        start_date: Optional start date for filtering (format: 'YYYY-MM-DD')
        end_date: Optional end date for filtering (format: 'YYYY-MM-DD')
    
    Returns:
        List of dictionaries containing memo entries with dalali payment information
    """
    memo_entry = Table('memo_entry')
    supplier = Table('supplier')
    party = Table('party')
    dalali_payments = Table('memo_dalali_payments')

    query = (
        Query.from_(memo_entry)
        .left_join(supplier).on(memo_entry.supplier_id == supplier.id)
        .left_join(party).on(memo_entry.party_id == party.id)
        .left_join(dalali_payments).on(memo_entry.id == dalali_payments.memo_id)
        .select(
            memo_entry.id,
            memo_entry.memo_number,
            memo_entry.supplier_id,
            supplier.name.as_('supplier_name'),
            memo_entry.party_id,
            party.name.as_('party_name'),
            memo_entry.amount,
            memo_entry.register_date,
            dalali_payments.id.as_('dalali_payment_id'),
            dalali_payments.is_paid,
            dalali_payments.paid_amount,
            dalali_payments.remark,
            dalali_payments.last_update.as_('dalali_last_update')
        )
    )
    
    # Add date range filters if provided
    if start_date:
        query = query.where(memo_entry.register_date >= start_date)
    if end_date:
        query = query.where(memo_entry.register_date <= end_date)
    
    # Add ordering
    query = query.orderby(memo_entry.register_date, order=Order.desc)
    
    sql = query.get_sql()

    response = execute_query(sql)
    result = response['result']
    
    # Bulk-load pair commission overrides so each row uses its supplier+party rate
    rates_by_pair = {}
    try:
        rates_table = Table('commission_rates')
        rates_query = Query.from_(rates_table).select(
            rates_table.supplier_id, rates_table.party_id, rates_table.rate_percent)
        rates_response = execute_query(rates_query.get_sql())
        if rates_response.get('status') == 'okay':
            rates_by_pair = {
                (row['supplier_id'], row['party_id']): float(row['rate_percent'])
                for row in rates_response['result']
            }
    except Exception:
        pass

    # Calculate commission amount and amount without GST for each memo entry
    for entry in result:
        if entry['amount'] is not None:
            rate_percent = rates_by_pair.get((entry['supplier_id'], entry['party_id']), 2.0)
            commission_result = calculate_commission(float(entry['amount']), rate_percent=rate_percent)
            entry['amount_without_gst'] = commission_result['amount_without_gst']
            entry['commission_amount'] = commission_result['commission']
        else:
            entry['amount_without_gst'] = 0
            entry['commission_amount'] = 0
            
        # If no dalali payment record exists, set default values
        if entry['dalali_payment_id'] is None:
            entry['is_paid'] = False
            entry['paid_amount'] = 0
            entry['remark'] = ''
    
    return result

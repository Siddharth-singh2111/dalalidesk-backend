"""
Utility functions for report generation
"""
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Union
import pandas as pd
from io import BytesIO


def calculate_financial_year(date: datetime) -> str:
    """
    Calculate the financial year (April to March) from a given date.
    
    Args:
        date: The date to calculate the financial year for
        
    Returns:
        A string in the format "YYYY-YYYY" representing the financial year
    """
    if date.month >= 4:  # April to December
        return f"{date.year}-{date.year + 1}"
    else:  # January to March
        return f"{date.year - 1}-{date.year}"


def apply_excel_formatting(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
    """
    Apply formatting to an Excel worksheet.
    
    Args:
        writer: The ExcelWriter object
        sheet_name: The name of the sheet to format
        df: The DataFrame being written to the sheet
    """
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    date_format = workbook.add_format({'num_format': 'dd-mm-yyyy'})
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    
    # Set column widths
    worksheet.set_column('A:A', 6)  # S.No
    worksheet.set_column('B:B', 15)  # Financial Year
    worksheet.set_column('C:C', 25)  # Supplier
    worksheet.set_column('D:D', 25)  # Party
    worksheet.set_column('E:E', 15)  # City
    worksheet.set_column('F:F', 12)  # Memo No
    worksheet.set_column('G:G', 15)  # Memo Date
    worksheet.set_column('H:S', 15)  # Other columns
    
    # Apply header formatting
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
    
    # Apply date formatting to date columns
    date_columns = ['MEMO DATE', 'DALALI ENTRY DATE', 'APPROVAL DATE']
    for date_col in date_columns:
        if date_col in df.columns:
            col_idx = df.columns.get_loc(date_col)
            for row in range(1, len(df) + 1):
                # Handle different date types safely
                cell_value = df.iloc[row-1, col_idx]
                if pd.notna(cell_value):
                    try:
                        # If it's already a string from Pydantic serialization, write as string
                        if isinstance(cell_value, str):
                            worksheet.write_string(row, col_idx, cell_value)
                        # If it's a datetime, format it
                        elif isinstance(cell_value, datetime):
                            worksheet.write_datetime(row, col_idx, cell_value, date_format)
                        # For any other type, convert to string
                        else:
                            worksheet.write_string(row, col_idx, str(cell_value))
                    except Exception as e:
                        # If there's an error, write it as a string
                        print(f"Error formatting date in row {row}, column {date_col}: {e}")
                        worksheet.write_string(row, col_idx, str(cell_value))
    
    # Apply number formatting to amount columns
    amount_columns = ['DD AMOUNT', 'LESS GST', 'NET AMOUNT', 'PAID AMOUNT', 
                      'TDS DEDUCTION', 'OTHER DEDUCTION']
    for amount_col in amount_columns:
        if amount_col in df.columns:
            col_idx = df.columns.get_loc(amount_col)
            for row in range(1, len(df) + 1):
                if pd.notna(df.iloc[row-1, col_idx]):
                    worksheet.write_number(row, col_idx, df.iloc[row-1, col_idx], number_format)
    
    # Enable filtering
    worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)


def generate_excel_file(df: pd.DataFrame, sheet_name: str = "Report") -> BytesIO:
    """
    Generate an Excel file from a pandas DataFrame.
    
    Args:
        df: The DataFrame to convert to Excel
        sheet_name: The name of the sheet in the Excel file
        
    Returns:
        A BytesIO object containing the Excel file
    """
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        apply_excel_formatting(writer, sheet_name, df)
    
    output.seek(0)
    return output

def generate_multi_sheet_excel_file(sheets_data: Dict[str, pd.DataFrame]) -> BytesIO:
    """
    Generate an Excel file with multiple sheets from pandas DataFrames.
    
    Args:
        sheets_data: Dictionary where keys are sheet names and values are DataFrames
        
    Returns:
        A BytesIO object containing the Excel file with multiple sheets
    """
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in sheets_data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            apply_excel_formatting(writer, sheet_name, df)
    
    output.seek(0)
    return output

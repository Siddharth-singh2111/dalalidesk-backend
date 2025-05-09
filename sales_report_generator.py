import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime
import calendar
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_database():
    """Establish a connection to the PostgreSQL database"""
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')
    
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return create_engine(db_url)

def get_month_year_range(start_year=2023, end_year=2025):
    """Generate a list of month names and a list of years for the report"""
    months = list(calendar.month_name)[1:]  # Get month names without empty first item
    years = list(range(start_year, end_year + 1))
    return months, years

def get_monthly_sales_data(engine, start_year=2023, end_year=2025):
    """Query the database to get monthly sales data aggregated by year and month"""
    query = text("""
        SELECT 
            EXTRACT(YEAR FROM register_date) AS year,
            EXTRACT(MONTH FROM register_date) AS month,
            SUM(amount) AS total_amount,
            SUM(gr_amount) AS total_gr_amount,
            SUM(deduction) AS total_deduction
        FROM 
            register_entry
        WHERE 
            EXTRACT(YEAR FROM register_date) BETWEEN :start_year AND :end_year
        GROUP BY 
            EXTRACT(YEAR FROM register_date),
            EXTRACT(MONTH FROM register_date)
        ORDER BY 
            year, month
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"start_year": start_year, "end_year": end_year})
        rows = result.fetchall()
    
    # Create a dictionary to store the results
    data = {
        'gross': {},
        'gr_amount': {},
        'deduction': {},
        'net': {}
    }
    
    for category in data:
        for year in range(start_year, end_year + 1):
            data[category][str(year)] = [0] * 12  # Initialize with zeros for all months
    
    # Fill in the data from the query results
    for row in rows:
        year = int(row[0])
        month = int(row[1])
        gross_amount = row[2] or 0
        gr_amount = row[3] or 0
        deduction = row[4] or 0
        net_amount = gross_amount - gr_amount - deduction
        
        year_str = str(year)
        if year_str in data['gross']:
            data['gross'][year_str][month - 1] = gross_amount
            data['gr_amount'][year_str][month - 1] = gr_amount
            data['deduction'][year_str][month - 1] = deduction
            data['net'][year_str][month - 1] = net_amount
    
    return data

def get_supplier_sales_data(engine, start_year=2023, end_year=2025):
    """Query the database to get supplier-wise sales data aggregated by year and month"""
    query = text("""
        SELECT 
            s.id AS supplier_id,
            s.name AS supplier_name,
            EXTRACT(YEAR FROM re.register_date) AS year,
            EXTRACT(MONTH FROM re.register_date) AS month,
            SUM(re.amount) AS total_amount,
            SUM(re.gr_amount) AS total_gr_amount,
            SUM(re.deduction) AS total_deduction
        FROM 
            register_entry re
        JOIN 
            supplier s ON re.supplier_id = s.id
        WHERE 
            EXTRACT(YEAR FROM re.register_date) BETWEEN :start_year AND :end_year
        GROUP BY 
            s.id, s.name, EXTRACT(YEAR FROM re.register_date), EXTRACT(MONTH FROM re.register_date)
        ORDER BY 
            SUM(re.amount - re.gr_amount - re.deduction) DESC, s.name, year, month
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"start_year": start_year, "end_year": end_year})
        rows = result.fetchall()
    
    # Process the results to get supplier totals for sorting
    supplier_totals = {}
    supplier_data = {}
    
    for row in rows:
        supplier_id = row[0]
        supplier_name = row[1]
        year = int(row[2])
        month = int(row[3])
        gross_amount = row[4] or 0
        gr_amount = row[5] or 0
        deduction = row[6] or 0
        net_amount = gross_amount - gr_amount - deduction
        
        # Initialize supplier data structure if not exists
        if supplier_id not in supplier_data:
            supplier_data[supplier_id] = {
                'name': supplier_name,
                'data': {
                    'gross': {},
                    'gr_amount': {},
                    'deduction': {},
                    'net': {}
                }
            }
            for category in supplier_data[supplier_id]['data']:
                for y in range(start_year, end_year + 1):
                    supplier_data[supplier_id]['data'][category][str(y)] = [0] * 12
            supplier_totals[supplier_id] = 0
        
        # Add sales data
        supplier_data[supplier_id]['data']['gross'][str(year)][month - 1] = gross_amount
        supplier_data[supplier_id]['data']['gr_amount'][str(year)][month - 1] = gr_amount
        supplier_data[supplier_id]['data']['deduction'][str(year)][month - 1] = deduction
        supplier_data[supplier_id]['data']['net'][str(year)][month - 1] = net_amount
        supplier_totals[supplier_id] += net_amount
    
    # Sort suppliers by total net sales
    sorted_suppliers = sorted(supplier_data.keys(), key=lambda x: supplier_totals[x], reverse=True)
    
    return [supplier_data[sid] for sid in sorted_suppliers]

def get_party_sales_data(engine, start_year=2023, end_year=2025):
    """Query the database to get party-wise sales data aggregated by year and month"""
    query = text("""
        SELECT 
            p.id AS party_id,
            p.name AS party_name,
            EXTRACT(YEAR FROM re.register_date) AS year,
            EXTRACT(MONTH FROM re.register_date) AS month,
            SUM(re.amount) AS total_amount,
            SUM(re.gr_amount) AS total_gr_amount,
            SUM(re.deduction) AS total_deduction
        FROM 
            register_entry re
        JOIN 
            party p ON re.party_id = p.id
        WHERE 
            EXTRACT(YEAR FROM re.register_date) BETWEEN :start_year AND :end_year
        GROUP BY 
            p.id, p.name, EXTRACT(YEAR FROM re.register_date), EXTRACT(MONTH FROM re.register_date)
        ORDER BY 
            SUM(re.amount - re.gr_amount - re.deduction) DESC, p.name, year, month
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"start_year": start_year, "end_year": end_year})
        rows = result.fetchall()
    
    # Process the results to get party totals for sorting
    party_totals = {}
    party_data = {}
    
    for row in rows:
        party_id = row[0]
        party_name = row[1]
        year = int(row[2])
        month = int(row[3])
        gross_amount = row[4] or 0
        gr_amount = row[5] or 0
        deduction = row[6] or 0
        net_amount = gross_amount - gr_amount - deduction
        
        # Initialize party data structure if not exists
        if party_id not in party_data:
            party_data[party_id] = {
                'name': party_name,
                'data': {
                    'gross': {},
                    'gr_amount': {},
                    'deduction': {},
                    'net': {}
                }
            }
            for category in party_data[party_id]['data']:
                for y in range(start_year, end_year + 1):
                    party_data[party_id]['data'][category][str(y)] = [0] * 12
            party_totals[party_id] = 0
        
        # Add sales data
        party_data[party_id]['data']['gross'][str(year)][month - 1] = gross_amount
        party_data[party_id]['data']['gr_amount'][str(year)][month - 1] = gr_amount
        party_data[party_id]['data']['deduction'][str(year)][month - 1] = deduction
        party_data[party_id]['data']['net'][str(year)][month - 1] = net_amount
        party_totals[party_id] += net_amount
    
    # Sort parties by total net sales
    sorted_parties = sorted(party_data.keys(), key=lambda x: party_totals[x], reverse=True)
    
    return [party_data[pid] for pid in sorted_parties]

def create_monthly_sales_sheet(writer, months, years, data):
    """Create a sheet showing monthly sales data with gross, deductions, and net values"""
    # Create DataFrames for each type of data
    df_gross = pd.DataFrame(index=months)
    df_gr = pd.DataFrame(index=months)
    df_deduction = pd.DataFrame(index=months)
    df_net = pd.DataFrame(index=months)
    
    # Add year columns with their corresponding monthly data
    for year in years:
        df_gross[f'Year {year}'] = data['gross'][str(year)]
        df_gr[f'Year {year}'] = data['gr_amount'][str(year)]
        df_deduction[f'Year {year}'] = data['deduction'][str(year)]
        df_net[f'Year {year}'] = data['net'][str(year)]
    
    # Add total columns
    df_gross['Total'] = df_gross.sum(axis=1)
    df_gr['Total'] = df_gr.sum(axis=1)
    df_deduction['Total'] = df_deduction.sum(axis=1)
    df_net['Total'] = df_net.sum(axis=1)
    
    # Add total rows
    totals_gross = df_gross.sum()
    totals_gr = df_gr.sum()
    totals_deduction = df_deduction.sum()
    totals_net = df_net.sum()
    
    df_gross.loc['Total'] = totals_gross
    df_gr.loc['Total'] = totals_gr
    df_deduction.loc['Total'] = totals_deduction
    df_net.loc['Total'] = totals_net
    
    # Write to Excel - Create four sections in the sheet
    worksheet_name = 'Monthly Sales'
    df_gross.to_excel(writer, sheet_name=worksheet_name, startrow=1, index=True)
    
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets[worksheet_name]
    
    # Determine the position for the next sections
    gross_rows = len(months) + 3  # +3 for header and total row and an empty row
    
    # Write section headers
    worksheet.write(0, 0, 'Gross Sales', workbook.add_format({'bold': True, 'font_size': 12}))
    worksheet.write(gross_rows, 0, 'GR Amount', workbook.add_format({'bold': True, 'font_size': 12}))
    worksheet.write(gross_rows * 2, 0, 'Deductions', workbook.add_format({'bold': True, 'font_size': 12}))
    worksheet.write(gross_rows * 3, 0, 'Net Sales', workbook.add_format({'bold': True, 'font_size': 12}))
    
    # Write the other sections
    df_gr.to_excel(writer, sheet_name=worksheet_name, startrow=gross_rows + 1, index=True)
    df_deduction.to_excel(writer, sheet_name=worksheet_name, startrow=gross_rows * 2 + 1, index=True)
    df_net.to_excel(writer, sheet_name=worksheet_name, startrow=gross_rows * 3 + 1, index=True)
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    total_format = workbook.add_format({
        'bold': True,
        'fg_color': '#FFC7CE',
        'border': 1,
        'num_format': '₹#,##0'
    })
    
    gross_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1
    })
    
    deduction_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1,
        'fg_color': '#FFE4E1'  # Light red for deductions
    })
    
    gr_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1,
        'fg_color': '#FFE4E1'  # Light red for GR amount
    })
    
    net_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1,
        'fg_color': '#E6FFE6'  # Light green for net
    })
    
    # Apply header formats to all sections
    for section_start in [1, gross_rows + 1, gross_rows * 2 + 1, gross_rows * 3 + 1]:
        for col_num, value in enumerate(['Month'] + [f'Year {year}' for year in years] + ['Total']):
            worksheet.write(section_start, col_num, value, header_format)
    
    # Set column widths
    worksheet.set_column(0, 0, 12)
    worksheet.set_column(1, len(years) + 1, 15)
    
    # Apply number formatting to all sections
    apply_format_to_range = lambda start_row, format_obj: worksheet.conditional_format(
        start_row + 1, 1, 
        start_row + len(months) + 1, len(years) + 1,
        {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': format_obj}
    )
    
    apply_format_to_range(1, gross_format)  # Gross sales
    apply_format_to_range(gross_rows + 1, gr_format)  # GR amount
    apply_format_to_range(gross_rows * 2 + 1, deduction_format)  # Deductions
    apply_format_to_range(gross_rows * 3 + 1, net_format)  # Net sales
    
    # Apply total format to all total rows
    for section_start in [1, gross_rows + 1, gross_rows * 2 + 1, gross_rows * 3 + 1]:
        last_row = section_start + len(months) + 1
        worksheet.conditional_format(
            last_row, 0, last_row, len(years) + 1,
            {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': total_format}
        )
    
    # Apply total format to all total columns
    for section_start in [1, gross_rows + 1, gross_rows * 2 + 1, gross_rows * 3 + 1]:
        last_col = len(years) + 1
        worksheet.conditional_format(
            section_start + 1, last_col, section_start + len(months) + 1, last_col,
            {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': total_format}
        )
    
    return df_net  # Return the net sales dataframe

def create_supplier_sales_sheet(writer, months, years, monthly_data, supplier_data):
    """Create a sheet showing supplier-wise sales data"""
    # First, create the monthly summary section
    df_monthly = pd.DataFrame(index=months)
    
    # Add year columns with their corresponding monthly data
    for year in years:
        df_monthly[f'Year {year}'] = monthly_data['net'][str(year)]  # Use net values instead of gross
    
    # Add a total column
    df_monthly['Total'] = df_monthly.sum(axis=1)
    
    # Add a total row
    totals = df_monthly.sum()
    df_monthly.loc['Total'] = totals
    
    # Create a DataFrame for the output
    df = pd.DataFrame(df_monthly)
    
    # Add a separator row
    separator = pd.DataFrame({col: [np.nan] for col in df.columns}, 
                            index=['Supplier Breakdown'])
    df = pd.concat([df, separator])
    
    # Add supplier data
    for supplier in supplier_data:
        # Create a mini DataFrame for this supplier
        supplier_rows = []
        supplier_name = supplier['name']
        
        # Create the supplier's row for each month
        for i, month in enumerate(months):
            row = [supplier_name + ' - ' + month]
            for year in years:
                row.append(supplier['data']['net'][str(year)][i])  # Use net values
            # Add total for the month across years
            row.append(sum(supplier['data']['net'][str(year)][i] for year in years))
            supplier_rows.append(row)
        
        # Add supplier total row
        total_row = [supplier_name + ' - Total']
        for year in years:
            total_row.append(sum(supplier['data']['net'][str(year)]))
        total_row.append(sum(total_row[1:]))
        supplier_rows.append(total_row)
        
        # Convert to DataFrame and add to main DataFrame
        supplier_df = pd.DataFrame(
            supplier_rows,
            columns=['Supplier'] + [f'Year {year}' for year in years] + ['Total']
        )
        supplier_df = supplier_df.set_index('Supplier')
        df = pd.concat([df, supplier_df])
    
    # Write to Excel
    df.to_excel(writer, sheet_name='Supplier Sales', index=True)
    
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Supplier Sales']
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    total_format = workbook.add_format({
        'bold': True,
        'fg_color': '#FFC7CE',
        'border': 1,
        'num_format': '₹#,##0'
    })
    
    supplier_header_format = workbook.add_format({
        'bold': True,
        'fg_color': '#B8CCE4',
        'border': 1
    })
    
    supplier_total_format = workbook.add_format({
        'bold': True,
        'fg_color': '#E6B8B7',
        'border': 1,
        'num_format': '₹#,##0'
    })
    
    currency_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1
    })
    
    # Apply formats
    for col_num, value in enumerate(['Entity'] + [f'Year {year}' for year in years] + ['Total']):
        worksheet.write(0, col_num, value, header_format)
    
    # Format numbers and set column width
    worksheet.set_column(0, 0, 30)
    worksheet.set_column(1, len(years) + 1, 15, currency_format)
    
    # Apply formatting to special rows
    current_row = 1
    
    # Format the monthly summary section
    for i in range(len(months) + 1):  # +1 for the total row
        if i == len(months):  # This is the total row
            worksheet.set_row(current_row, None, total_format)
        current_row += 1
    
    # Format the separator row
    worksheet.set_row(current_row, None, supplier_header_format)
    current_row += 1
    
    # Format supplier sections
    for supplier in supplier_data:
        # Skip to the last row of each supplier section (total row)
        current_row += len(months)
        worksheet.set_row(current_row, None, supplier_total_format)
        current_row += 1
    
    # Add title
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter'
    })
    worksheet.merge_range('A1:E1', 'Supplier-wise Net Sales (After GR and Deductions)', title_format)
    
    return df

def create_party_sales_sheet(writer, months, years, monthly_data, party_data):
    """Create a sheet showing party-wise sales data"""
    # First, create the monthly summary section
    df_monthly = pd.DataFrame(index=months)
    
    # Add year columns with their corresponding monthly data
    for year in years:
        df_monthly[f'Year {year}'] = monthly_data['net'][str(year)]  # Use net values instead of gross
    
    # Add a total column
    df_monthly['Total'] = df_monthly.sum(axis=1)
    
    # Add a total row
    totals = df_monthly.sum()
    df_monthly.loc['Total'] = totals
    
    # Create a DataFrame for the output
    df = pd.DataFrame(df_monthly)
    
    # Add a separator row
    separator = pd.DataFrame({col: [np.nan] for col in df.columns}, 
                            index=['Party Breakdown'])
    df = pd.concat([df, separator])
    
    # Add party data
    for party in party_data:
        # Create a mini DataFrame for this party
        party_rows = []
        party_name = party['name']
        
        # Create the party's row for each month
        for i, month in enumerate(months):
            row = [party_name + ' - ' + month]
            for year in years:
                row.append(party['data']['net'][str(year)][i])  # Use net values
            # Add total for the month across years
            row.append(sum(party['data']['net'][str(year)][i] for year in years))
            party_rows.append(row)
        
        # Add party total row
        total_row = [party_name + ' - Total']
        for year in years:
            total_row.append(sum(party['data']['net'][str(year)]))
        total_row.append(sum(total_row[1:]))
        party_rows.append(total_row)
        
        # Convert to DataFrame and add to main DataFrame
        party_df = pd.DataFrame(
            party_rows,
            columns=['Party'] + [f'Year {year}' for year in years] + ['Total']
        )
        party_df = party_df.set_index('Party')
        df = pd.concat([df, party_df])
    
    # Write to Excel
    df.to_excel(writer, sheet_name='Party Sales', index=True)
    
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets['Party Sales']
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    total_format = workbook.add_format({
        'bold': True,
        'fg_color': '#FFC7CE',
        'border': 1,
        'num_format': '₹#,##0'
    })
    
    party_header_format = workbook.add_format({
        'bold': True,
        'fg_color': '#B8CCE4',
        'border': 1
    })
    
    party_total_format = workbook.add_format({
        'bold': True,
        'fg_color': '#E6B8B7',
        'border': 1,
        'num_format': '₹#,##0'
    })
    
    currency_format = workbook.add_format({
        'num_format': '₹#,##0',
        'border': 1
    })
    
    # Apply formats
    for col_num, value in enumerate(['Entity'] + [f'Year {year}' for year in years] + ['Total']):
        worksheet.write(0, col_num, value, header_format)
    
    # Format numbers and set column width
    worksheet.set_column(0, 0, 30)
    worksheet.set_column(1, len(years) + 1, 15, currency_format)
    
    # Apply formatting to special rows
    current_row = 1
    
    # Format the monthly summary section
    for i in range(len(months) + 1):  # +1 for the total row
        if i == len(months):  # This is the total row
            worksheet.set_row(current_row, None, total_format)
        current_row += 1
    
    # Format the separator row
    worksheet.set_row(current_row, None, party_header_format)
    current_row += 1
    
    # Format party sections
    for party in party_data:
        # Skip to the last row of each party section (total row)
        current_row += len(months)
        worksheet.set_row(current_row, None, party_total_format)
        current_row += 1
    
    # Add title
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter'
    })
    worksheet.merge_range('A1:E1', 'Party-wise Net Sales (After GR and Deductions)', title_format)
    
    return df

def generate_sales_report(start_year=2023, end_year=2025, output_path=None):
    """
    Generate an Excel report showing sales data by month, supplier, and party
    
    Args:
        start_year (int): The starting year for the report
        end_year (int): The ending year for the report
        output_path (str, optional): The output file path. If None, the file will be saved in the current directory.
    
    Returns:
        str: The path to the generated Excel file
    """
    # If output_path is None, save in the current directory
    if output_path is None:
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"sales_report_{current_datetime}.xlsx")
    
    # Connect to the database
    engine = connect_to_database()
    
    # Get month and year ranges
    months, years = get_month_year_range(start_year, end_year)
    
    # Get data from the database
    monthly_data = get_monthly_sales_data(engine, start_year, end_year)
    supplier_data = get_supplier_sales_data(engine, start_year, end_year)
    party_data = get_party_sales_data(engine, start_year, end_year)
    
    # Create Excel file
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # Create sheets
        create_monthly_sales_sheet(writer, months, years, monthly_data)
        create_supplier_sales_sheet(writer, months, years, monthly_data, supplier_data)
        create_party_sales_sheet(writer, months, years, monthly_data, party_data)
    
    print(f"Sales report generated: {output_path}")
    return output_path

if __name__ == "__main__":
    # Generate the report for years 2023-2025
    report_path = generate_sales_report(2023, 2025)
    print(f"Report saved to: {report_path}")

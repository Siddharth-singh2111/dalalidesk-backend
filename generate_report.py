#!/usr/bin/env python3
import argparse
import os
from sales_report_generator import generate_sales_report

def main():
    parser = argparse.ArgumentParser(description='Generate sales report Excel file')
    parser.add_argument('--start-year', type=int, default=2023,
                        help='Starting year for the report (default: 2023)')
    parser.add_argument('--end-year', type=int, default=2025,
                        help='Ending year for the report (default: 2025)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output file path (default: sales_report_<timestamp>.xlsx in the current directory)')
    
    args = parser.parse_args()
    
    # Generate the report
    output_path = generate_sales_report(
        start_year=args.start_year,
        end_year=args.end_year,
        output_path=args.output
    )
    
    print(f"Report successfully generated: {output_path}")

if __name__ == "__main__":
    main()

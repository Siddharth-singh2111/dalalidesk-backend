"""
=== Class Description ===
The file is supposed to represent a Supplier

"""
from __future__ import annotations
from API_Database import retrieve_indivijual
from .Individual import Individual

class Supplier(Individual):
    """
    The class represents a supplier.

    name : The name  of the Supplier
    short_name: The short name of the Supplier
    address: The address of the supplier.

    """
    table_name = 'supplier'

    def __init__(self, name: str, address: str, *args, **kwargs) -> None:
        """Initializes a Supplier instance by invoking the parent initializer with a preset table name."""
        super().__init__(name, address, table_name=self.table_name, **kwargs)

    @staticmethod
    def get_supplier_name_by_id(supplier_id: int) -> str:
        """
        Get supplier name by ID
        """
        return retrieve_indivijual.get_supplier_name_by_id(supplier_id)

    @staticmethod
    def get_report_name(supplier_id: int) -> str:
        """
        Get supplier name by ID for report
        """
        return 'Supplier Name: ' + retrieve_indivijual.get_supplier_name_by_id(supplier_id)
        
    @staticmethod
    def format_gst_percentage(gst_value: float) -> str:
        """
        Format a GST decimal value as a percentage string.
        
        Args:
            gst_value: The GST value as a decimal (e.g., 5.0, 12.0, 4.762)
            
        Returns:
            str: The formatted GST percentage string (e.g., "5%", "12%", "4.762%")
        """
        if gst_value is None:
            return None
        return f"{gst_value}%"
        
    def get_gst_default_formatted(self) -> str:
        """
        Get the supplier's default GST rate formatted as a percentage string.
        
        Returns:
            str: The formatted GST percentage string (e.g., "5%", "12%", "4.762%")
        """
        if self.gst_default is None:
            return None
        return self.format_gst_percentage(self.gst_default)

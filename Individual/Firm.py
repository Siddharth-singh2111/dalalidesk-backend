"""
=== Class Description ===
The file is supposed to represent a Firm
"""
from __future__ import annotations
from API_Database import retrieve_indivijual
from .Individual import Individual

class Firm(Individual):
    """
    The class represents a firm.

    name: The name of the Firm
    address: The address of the Firm
    """
    table_name = 'firm'

    def __init__(self, name: str, address: str, *args, **kwargs) -> None:
        """Initializes a Firm instance by invoking the parent initializer with a preset table name."""
        super().__init__(name, address, table_name=self.table_name, **kwargs)

    @staticmethod
    def get_firm_name_by_id(firm_id: int) -> str:
        """
        Get firm name by ID
        """
        return retrieve_indivijual.get_firm_name_by_id(firm_id)

    @staticmethod
    def get_report_name(firm_id: int) -> str:
        """
        Get firm name by ID for report
        """
        return 'Firm Name: ' + retrieve_indivijual.get_firm_name_by_id(firm_id)

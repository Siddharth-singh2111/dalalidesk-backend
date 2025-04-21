"""
=== Class Description ===
The file is supposed to represent a Firm Bank
"""
from __future__ import annotations
from typing import Dict, Optional
from API_Database import retrieve_indivijual
from .Individual import Individual

class FirmBank(Individual):
    """
    The class represents a firm bank.

    name: The name of the Firm Bank
    address: The address of the Firm Bank
    firm_id: The ID of the associated Firm
    """
    table_name = 'firm_bank'

    def __init__(self, name: str, address: str, firm_id: int, *args, **kwargs) -> None:
        """Initializes a FirmBank instance by invoking the parent initializer with a preset table name."""
        self.firm_id = firm_id
        super().__init__(name, address, table_name=self.table_name, **kwargs)

    def update(self, current_user_id: Optional[int] = None) -> Dict:
        """
        Override update to include firm_id
        """
        from psql import execute_query
        
        entity_id = self.get_id()
        update_fields = [f"name='{self.name}'", f"address='{self.address}'", f"firm_id={self.firm_id}"]
        if self.phone_number:
            update_fields.append(f"phone_number='{self.phone_number}'")
            
        # Add audit fields
        if current_user_id is not None:
            update_fields.append(f"last_updated=CURRENT_TIMESTAMP")
            update_fields.append(f"last_updated_by={current_user_id}")
            
        update_str = ', '.join(update_fields)
        sql = f'UPDATE {self.table_name} SET {update_str} WHERE id={entity_id}'
        
        return execute_query(sql, current_user_id=current_user_id)

    @classmethod
    def insert(cls, obj: Dict, get_cls: bool=False, current_user_id: Optional[int] = None) -> Dict:
        """
        Override insert to include firm_id
        """
        from psql import execute_query
        
        entity = cls.from_dict(obj)
        
        # Build the INSERT query
        def remove_single_quotes(value):
            """Removes single quotes from a string to avoid SQL injection issues."""
            return value.replace("'", '')
            
        columns = ['name', 'address', 'firm_id']
        values = [
            f"'{remove_single_quotes(entity.name)}'", 
            f"'{remove_single_quotes(entity.address)}'",
            str(entity.firm_id)
        ]
        
        if entity.phone_number is not None:
            columns.append('phone_number')
            values.append(f"'{entity.phone_number}'")
            
        # Add audit fields
        if current_user_id is not None:
            columns.append('created_by')
            values.append(str(current_user_id))
            columns.append('last_updated_by')
            values.append(str(current_user_id))
            
        columns_str = ', '.join(columns)
        values_str = ', '.join(values)
        
        sql = f'INSERT INTO {entity.table_name} ({columns_str}) VALUES ({values_str}) RETURNING id'
        
        result = execute_query(sql, current_user_id=current_user_id)
        
        if result['status'] == 'okay' and result['result']:
            entity.id = result['result'][0]['id']
            if get_cls:
                result['class'] = entity
                
        return result

    @staticmethod
    def get_firm_bank_name_by_id(firm_bank_id: int) -> str:
        """
        Get firm bank name by ID
        """
        return retrieve_indivijual.get_firm_bank_name_by_id(firm_bank_id)

    @staticmethod
    def get_report_name(firm_bank_id: int) -> str:
        """
        Get firm bank name by ID for report
        """
        return 'Firm Bank Name: ' + retrieve_indivijual.get_firm_bank_name_by_id(firm_bank_id)

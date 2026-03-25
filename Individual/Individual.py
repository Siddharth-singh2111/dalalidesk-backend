"""
=== Class Description ===
The file is supposed to represent a Individual
"""
from __future__ import annotations
from typing import Dict, Optional
from datetime import datetime
import re
import phonenumbers
from API_Database import get_individual_id_by_name, insert_individual
from API_Database import get_individual_by_id, update_individual
from API_Database import delete_by_id
from API_Database.audit_log import get_audit_history
from Exceptions import DataError

class Individual:
    """
    The class represents a Individual.

    name : The name of the Individual
    short_name: The short name of the Individual
    address: The address of the Individual.
    """

    def __init__(self, name: str, address: str, table_name: str, *args, **kwargs):
        """
        Initialize an Individual.
        
        Args:
            name: The name of the Individual
            address: The address of the Individual
            table_name: The name of the database table
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments including:
                phone_number: The phone number of the Individual
                id: The primary key ID
                created_at: When the Individual was created
                created_by: Who created the Individual
                last_updated: When the Individual was last updated
                last_updated_by: Who last updated the Individual
        """
        self.name = name
        self.address = address
        phone_number = kwargs.get('phone_number', None)
        self.phone_number = self._parse_number(phone_number)
        city = kwargs.get('city', None)
        self.city = city
        gst_default = kwargs.get('gst_default', None)
        self.gst_default = gst_default
        self.gstin = None
        if table_name == 'supplier' and 'gstin' in kwargs:
            raw = kwargs.get('gstin')
            if raw is not None and str(raw).strip():
                self.gstin = re.sub(r'\s+', '', str(raw).strip()).upper()
        self.table_name = table_name
        self.id = kwargs.get('id', None)
        if self.id is not None:
            self.id = int(self.id)
            
        # Audit trail fields
        self.created_at = kwargs.get('created_at')
        self.created_by = kwargs.get('created_by')
        self.last_updated = kwargs.get('last_updated')
        self.last_updated_by = kwargs.get('last_updated_by')

    def get_id(self) -> int:
        """Returns the individual's ID, or retrieves it based on name if not already set."""
        if self.id is not None:
            return self.id
        return get_individual_id_by_name(self.name, self.table_name)

    def update(self, current_user_id: Optional[int] = None) -> Dict:
        """
        Update the individual's record in the database.
        
        Args:
            current_user_id: The ID of the user performing the update
            
        Returns:
            Dict: The result of the update operation
        """
        from psql import execute_query

        def _strip_quotes(value: str) -> str:
            return str(value).replace("'", "")

        entity_id = self.get_id()
        update_fields = [f"name='{self.name}'", f"address='{self.address}'"]
        if self.phone_number:
            update_fields.append(f"phone_number='{self.phone_number}'")
        if self.city:
            update_fields.append(f"city='{self.city}'")
        if self.gst_default is not None:
            update_fields.append(f"gst_default={self.gst_default}")
        if self.table_name == 'supplier':
            if self.gstin:
                update_fields.append(f"gstin='{_strip_quotes(self.gstin)}'")
            else:
                update_fields.append("gstin=NULL")
        # Add audit fields
        if current_user_id is not None:
            update_fields.append(f"last_updated=CURRENT_TIMESTAMP")
            update_fields.append(f"last_updated_by={current_user_id}")
            
        update_str = ', '.join(update_fields)
        sql = f'UPDATE {self.table_name} SET {update_str} WHERE id={entity_id}'
        
        return execute_query(sql, current_user_id=current_user_id)

    def delete(self, current_user_id: Optional[int] = None) -> Dict:
        """
        Delete the individual's record from the database.
        
        Args:
            current_user_id: The ID of the user performing the delete
            
        Returns:
            Dict: The result of the delete operation
        """
        from psql import execute_query
        
        query = f'DELETE from {self.table_name} where id={self.get_id()}'
        return execute_query(query, current_user_id=current_user_id)
        
    def get_audit_history(self, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get the audit history for this individual.
        
        Args:
            limit: The maximum number of records to return
            offset: The number of records to skip
            
        Returns:
            Dict: The audit history
        """
        if not self.id:
            return {
                'status': 'error',
                'message': 'Individual ID is required'
            }
            
        return get_audit_history(
            table_name=self.table_name,
            record_id=self.id,
            limit=limit,
            offset=offset
        )

    def _parse_number(self, number: str) -> str:
        """
        Checks if the number is a valid number. Defaults to "IN" (Indian) country code.
        
        Args:
            number: The phone number to parse
            
        Returns:
            str: The formatted phone number
            
        Raises:
            DataError: If the phone number is invalid
        """
        if number is None:
            return None
        if type(number) != str:
            print(f'WARNING: Provided phone number ({number}) is not a string.')
            number = str(number)
        parsed_number = phonenumbers.parse(number, 'IN')
        if not phonenumbers.is_valid_number(parsed_number):
            raise DataError({'status': 'error', 'message': 'Invalid Phone Number', 'input_errors': {'phone_number': {'error': True, 'message': 'Invalid Phone Number'}}})
        formatted_phone_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        return formatted_phone_number

    @classmethod
    def from_dict(cls, obj: Dict, *args, **kwargs) -> Individual:
        """
        Create an Individual instance from a dictionary.
        
        Args:
            obj: The dictionary containing individual data
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            Individual: A new Individual instance
        """
        return cls(**obj)

    @classmethod
    def retrieve(cls, id: int) -> Individual:
        """
        Retrieve an Individual by ID from the database.
        
        Args:
            id: The ID of the Individual to retrieve
            
        Returns:
            Individual: The retrieved Individual
        """
        return cls.from_dict(get_individual_by_id(id, cls.table_name))

    @classmethod
    def insert(cls, obj: Dict, get_cls: bool=False, current_user_id: Optional[int] = None) -> Dict:
        """
        Insert a new Individual into the database.
        
        Args:
            obj: The dictionary containing individual data
            get_cls: Whether to include the Individual instance in the result
            current_user_id: The ID of the user performing the insert
            
        Returns:
            Dict: The result of the insert operation
        """
        from psql import execute_query
        
        entity = cls.from_dict(obj)
        
        # Build the INSERT query
        def remove_single_quotes(value):
            """Removes single quotes from a string to avoid SQL injection issues."""
            return value.replace("'", '')
            
        columns = ['name', 'address']
        values = [f"'{remove_single_quotes(entity.name)}'", f"'{remove_single_quotes(entity.address)}'"]
        
        if entity.phone_number is not None:
            columns.append('phone_number')
            values.append(f"'{entity.phone_number}'")

        if entity.city is not None:
            columns.append('city')
            values.append(f"'{entity.city}'")

        if entity.gst_default is not None:
            columns.append('gst_default')
            values.append(f"{entity.gst_default}")

        if entity.table_name == 'supplier' and getattr(entity, 'gstin', None):
            columns.append('gstin')
            values.append(f"'{remove_single_quotes(entity.gstin)}'")

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

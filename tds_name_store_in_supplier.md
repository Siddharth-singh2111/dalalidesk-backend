Implementation Plan for Supplier TAN Numbers and TDS Names
1. Database Schema Changes
1.1. Create New Tables
Create supplier_tan and supplier_tds_name tables with foreign key relationships to supplier
Include audit fields (created_at, created_by, last_updated, last_updated_by) consistent with existing schema
Add unique constraints to prevent duplicates
Add sequences for ID generation
-- Placeholder for SQL schema changes
CREATE SEQUENCE supplier_tan_seq;
CREATE TABLE supplier_tan (
    id INT DEFAULT NEXTVAL ('supplier_tan_seq') PRIMARY KEY,
    supplier_id INT REFERENCES supplier(id) ON DELETE CASCADE,
    tan_number VARCHAR(20) NOT NULL,
    -- audit fields
    UNIQUE(supplier_id, tan_number)
);

CREATE SEQUENCE supplier_tds_name_seq;
CREATE TABLE supplier_tds_name (
    id INT DEFAULT NEXTVAL ('supplier_tds_name_seq') PRIMARY KEY,
    supplier_id INT REFERENCES supplier(id) ON DELETE CASCADE,
    tds_name VARCHAR(100) NOT NULL,
    -- audit fields
    UNIQUE(supplier_id, tds_name)
);
2. API_Database Layer Updates
2.1. Create New Modules
Create new modules in API_Database for:

retrieve_supplier_tan.py
Functions to get TAN numbers by supplier ID
Function to get TAN number details by ID
retrieve_supplier_tds_name.py
Functions to get TDS names by supplier ID
Function to get TDS name details by ID
2.2. Update Existing Module
Extend retrieve_individual.py to include:

Function get_supplier_with_tan_tds that includes TAN numbers and TDS names
Update get_individual_by_id when table_name is 'supplier' to include these relations
2.3. Create Insert/Update/Delete Modules
insert_supplier_tan.py
Functions to add new TAN numbers
insert_supplier_tds_name.py
Functions to add new TDS names
Update any relevant delete functions to handle cascading deletes or ensure deletion of related records
3. Supplier Class Updates
3.1. Extend Supplier Class in Supplier.py
Update __init__ to include:
self.tan_numbers = kwargs.get('tan_numbers', [])
self.tds_names = kwargs.get('tds_names', [])
3.2. Add Methods for TAN Management
get_tan_numbers()
add_tan_number(tan_number, current_user_id=None)
remove_tan_number(tan_id, current_user_id=None)
update_tan_numbers(tan_numbers_list, current_user_id=None) - for bulk update scenarios
3.3. Add Methods for TDS Name Management
get_tds_names()
add_tds_name(tds_name, current_user_id=None)
remove_tds_name(tds_id, current_user_id=None)
update_tds_names(tds_names_list, current_user_id=None) - for bulk update scenarios
3.4. Override delete Method
Override the delete method from Individual class to handle deletion of related records:

The database should handle cascading deletes through ON DELETE CASCADE
Update the method to ensure proper cleanup
3.5. Update Supplier.from_dict Method
Update or extend the from_dict method to handle TAN numbers and TDS names when creating Supplier objects from dictionaries.

4. API Endpoint Changes (app.py)
4.1. Update GET /supplier/{id}
Modify to include TAN numbers and TDS names in the response
4.2. Update PUT /supplier/{id}
Add handling for TAN numbers and TDS names updates
Implement diff detection to determine:
Which TAN numbers/TDS names to add (new ones)
Which to keep (existing ones)
Which to delete (removed ones)
4.3. Make POST /supplier Support TAN and TDS
Update to handle initial TAN numbers and TDS names during supplier creation
4.4. Add TAN/TDS-specific Endpoints (Optional)
Add endpoints for individual management of TAN numbers and TDS names
POST /supplier/{id}/tan
DELETE /supplier/{id}/tan/{tan_id}
POST /supplier/{id}/tds-name
DELETE /supplier/{id}/tds-name/{tds_id}
5. Search/Filter Functionality
5.1. Update Search Functions
Extend search functionality to include TAN numbers and TDS names in supplier searches
Implement specific filtering by TAN or TDS name
6. Testing
6.1. Unit Tests
Test basic CRUD operations for TAN numbers and TDS names
Test cascading deletes and proper cleanup
6.2. Integration Tests
Test API endpoints
Verify that supplier deletion properly cleans up TAN and TDS records
Implementation Sequence
Database schema changes - Create the new tables and relationships
Core API_Database modules - Implement retrieve, insert, update functions
Supplier class extensions - Update the class to handle the new relationships
API endpoint updates - Modify existing endpoints to support the new features
Testing and validation - Ensure all functionality works as expected
Search/filter integration - Implement filtering by TAN/TDS
Frontend integration - Update UI to support managing TAN/TDS (if applicable)
Is there any specific part of this plan you'd like me to elaborate on further or any adjustments you'd like to make before proceeding?
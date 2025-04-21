from Entities import RegisterEntry, MemoEntry, OrderForm, Item, ItemEntry
from Individual import Supplier, Party, Bank, Transporter, Firm, FirmBank
from Exceptions import DataError

def table_class_mapper(table_name: str):
    """Maps a table name to its corresponding entity class; raises a DataError if the table name is not recognized."""
    entity_mapping = {
        'supplier': Supplier, 
        'party': Party, 
        'bank': Bank, 
        'transport': Transporter, 
        'register_entry': RegisterEntry, 
        'memo_entry': MemoEntry, 
        'order_form': OrderForm, 
        'item': Item, 
        'item_entry': ItemEntry,
        'firm': Firm,
        'firm_bank': FirmBank
    }
    if table_name not in entity_mapping:
        raise DataError('Table name not found in entity mapping')
    return entity_mapping[table_name]

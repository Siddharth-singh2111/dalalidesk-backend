from typing import Dict
import json
from Reports import report
from API_Database import efficiency, retrieve_indivijual
import sys
sys.path.append('../')

def make_report(data: Dict) -> Dict:
    """Generates and returns a report based on provided data parameters."""
    supplier_all = data.get('supplierAll', False)
    party_all = data.get('partyAll', False)
    if supplier_all:
        supplier_data = retrieve_indivijual.get_all_names_ids('supplier')
        supplier_ids = [s['id'] for s in supplier_data]
    else:
        supplier_ids = [element['id'] for element in json.loads(data['suppliers'])]
    if party_all:
        party_data = retrieve_indivijual.get_all_names_ids('party')
        party_ids = [p['id'] for p in party_data]
    else:
        party_ids = [element['id'] for element in json.loads(data['parties'])]
    select = data['report']
    start_date = data['from']
    end_date = data['to']
    if isinstance(supplier_ids, int):
        supplier_ids = [supplier_ids]
    if isinstance(party_ids, int):
        party_ids = [party_ids]
    options = ['khata_report', 'supplier_register', 'payment_list', 'order_form']
    if select in options[0:4]:
        report_obj = report.Report(select, party_ids, supplier_ids, start_date, end_date)
        report_data = report_obj.generate_table(supplier_all=supplier_all, party_all=party_all)
        return report_data
    else:
        raise Exception('Invalid Option')
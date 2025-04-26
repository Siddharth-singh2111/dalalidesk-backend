import json
import signal
import sys
from typing import Dict, Union, List
from contextlib import contextmanager
from datetime import datetime, timedelta
from Individual import Supplier, Party
from Entities import RegisterEntry, MemoEntry, OrderForm, Item, ItemEntry
from Tests import TestKhataReport
from Reports import make_report
from Tests import check_status_and_return_class, cleanup, print_dict_diff
TEST_SUPPLIER_NAME = 'tes_spffli4334'
TEST_PARTY_NAME = 'test_sprjjj33'
TEST_BILL_NUMBER = '13456'
TEST_MEMO_NUMBER1 = 22707
TEST_MEMO_NUMBER2 = 370315
TODAY = datetime.now().date()
BILL_DATE = (TODAY - timedelta(days=180)).strftime('%Y-%m-%d')
ORDER_FORM_DATE = (TODAY - timedelta(days=182)).strftime('%Y-%m-%d')
MEMO_DATE = (TODAY - timedelta(days=120)).strftime('%Y-%m-%d')
DAYS_SINCE_BILL = (TODAY - datetime.strptime(BILL_DATE, '%Y-%m-%d').date()).days

def format_date_for_display(date_str):
    """Convert YYYY-MM-DD to DD/MM/YYYY format"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%d/%m/%Y')

@contextmanager
def cleanup_context(cleanup_list):
    """Context manager that yields the cleanup_list and calls cleanup(cleanup_list) upon exit."""
    try:
        yield cleanup_list
    finally:
        cleanup(cleanup_list)

def signal_handler(signum, frame):
    """Handles OS signals by printing an interrupt message and gracefully exiting the program."""
    print('Received interrupt, cleaning up...')
    sys.exit(0)

def item_test(supplier_id: int, cleanup_list: List) -> Item:
    """Creates an Item using test data, appends it to the cleanup_list, and returns the Item instance."""
    item_input = {'name': 'Super Shiny Saree11', 'supplier_id': supplier_id}
    test_item = check_status_and_return_class(Item.insert(item_input, get_cls=True))
    cleanup_list.append(test_item)
    return test_item

def item_entry_test(register_entry_id: int, item_id: int) -> ItemEntry:
    """Creates an ItemEntry using test data and returns the resulting ItemEntry."""
    item_entry_input = {'register_entry_id': register_entry_id, 'item_id': item_id, 'quantity': 10, 'rate': 1000}
    test_item_entry = check_status_and_return_class(ItemEntry.insert(item_entry_input, get_cls=True))
    return test_item_entry

def run_basic_test():
    """Executes the basic test flow: creating entities, generating reports, validating outputs, and performing cleanup."""
    cleanup_list = []
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    with cleanup_context(cleanup_list):
        try:
            cleanup_list = []
            test_supplier_input = {'name': TEST_SUPPLIER_NAME, 'address': 'test_address', 'phone_number': '9350544808'}
            test_party_input = {'name': TEST_PARTY_NAME, 'address': 'test_address', 'phone_number': '+1 647 901 4404'}
            test_supplier = check_status_and_return_class(Supplier.insert(test_supplier_input, get_cls=True))
            cleanup_list.append(test_supplier)
            test_supplier_id = test_supplier.get_id()
            test_supplier = Supplier.retrieve(test_supplier_id)
            test_supplier_id = test_supplier.get_id()
            test_party = check_status_and_return_class(Party.insert(test_party_input, get_cls=True))
            cleanup_list.append(test_party)
            test_party_id = test_party.get_id()
            test_party = Party.retrieve(test_party_id)
            test_item = item_test(test_supplier_id, cleanup_list)
            test_item_id = test_item.get_id()
            order_form_number = 1
            order_form_input = {'supplier_id': test_supplier_id, 'party_id': test_party_id, 'register_date': ORDER_FORM_DATE, 'order_form_number': order_form_number}
            test_order_form = check_status_and_return_class(OrderForm.insert(order_form_input, get_cls=True))
            cleanup_list.append(test_order_form)
            test_order_form = OrderForm.retrieve(test_supplier_id, test_party_id, order_form_number)
            og_report = make_report({'report': 'order_form', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': ORDER_FORM_DATE, 'to': BILL_DATE})
            order_form_data = og_report['headings'][0]['subheadings'][0]['dataRows'][0]
            try:
                assert int(order_form_data['order_no']) == order_form_number
                assert order_form_data['order_date'] == format_date_for_display(ORDER_FORM_DATE)
                assert order_form_data['supp_name'] == test_supplier_input['name']
                assert order_form_data['party_name'] == test_party_input['name']
                assert len(og_report['headings'][0]['subheadings']) == 1
            except AssertionError:
                print('\nDifference in order form report:')
                print_dict_diff(og_report, {'headings': [{'subheadings': [{'dataRows': [order_form_data]}]}]})
                raise
            bill_amount = 5000
            bill_input = {'bill_number': TEST_BILL_NUMBER, 'amount': bill_amount, 'supplier_id': test_supplier_id, 'party_id': test_party_id, 'register_date': BILL_DATE}
            register_entry = check_status_and_return_class(RegisterEntry.insert(bill_input, get_cls=True))

            cleanup_list.append(register_entry)
            register_entry = RegisterEntry.retrieve(test_supplier_id, test_party_id, TEST_BILL_NUMBER, BILL_DATE)
            register_entry_id = register_entry.get_id()
            og_report = make_report({'report': 'order_form', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            try:
                assert len(og_report['headings']) == 0
            except AssertionError:
                print('\nDifference in empty order form report:')
                print_dict_diff(og_report, {'headings': []})
                raise
            og_report = make_report({'report': 'khata_report', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            report = TestKhataReport('khata_report', [test_party_id], [test_supplier_id], BILL_DATE, BILL_DATE)
            report_data = report.generate_table([register_entry], [])
            test_item_entry = item_entry_test(register_entry_id, test_item_id)
            try:
                assert og_report == report_data
            except AssertionError:
                print('\nDifference in initial khata report:')
                print_dict_diff(og_report, report_data)
                raise
            pending_bills = RegisterEntry.get_pending_bills(test_supplier_id, test_party_id)
            total_pending_amount = bill_amount
            quarter_pending = total_pending_amount // 4
            og_payment_report = make_report({'report': 'payment_list', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            reference = {'title': 'Payment List', 'from': BILL_DATE, 'to': BILL_DATE, 'headings': [{'title': f'Party Name: {TEST_PARTY_NAME}', 'subheadings': [{'title': f'Supplier Name: {TEST_SUPPLIER_NAME}', 'dataRows': [{'part_no': '', 'part_date': '', 'part_amt': '', 'bill_no': int(TEST_BILL_NUMBER), 'bill_amt': '5,000', 'bill_date': format_date_for_display(BILL_DATE), 'pending_amt': 5000, 'days': DAYS_SINCE_BILL, 'status': 'N'}], 'specialRows': [{'name': 'Total (=)', 'value': '0', 'column': 'part_amt', 'numeric': 0, 'beforeData': False}, {'name': '<60 days (+)', 'value': '0', 'column': 'bill_amt', 'numeric': 0, 'beforeData': False}, {'name': '60-120 days (+)', 'value': '0', 'column': 'bill_amt', 'numeric': 0, 'beforeData': False}, {'name': '>120 days (+)', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}, {'name': 'Subtotal (=)', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}, {'name': 'Part (-)', 'value': '- 0', 'column': 'bill_amt', 'numeric': 0, 'beforeData': False}, {'name': 'Pending (=)', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}], 'displayOnIndex': True, 'cumulative': {'name': 'Total Pending', 'value': '5,000'}}], 'cumulative': {'name': 'Total Pending', 'value': '5,000'}}]}
            try:
                assert og_payment_report == reference
            except AssertionError:
                print('Difference in Payment List Report')
                print_dict_diff(og_payment_report, reference)
                raise
            part_input = {
    'memo_number': TEST_MEMO_NUMBER1, 
    'register_date': MEMO_DATE, 
    'amount': quarter_pending,
    'discount': 0,  # No discount for partial payment
    'other_deduction': 0,  # No other deduction for partial payment
    'rate_difference': 0,  # No rate difference for partial payment
    'party_id': test_party_id, 
    'supplier_id': test_supplier_id, 
    'payment': [{'bank': 'RTGS', 'id': 1, 'cheque': '234', 'amount': quarter_pending}],  # Add amount to payment
    'less_details': {
        'gr_amount': [],
        'discount': [],
        'other_deduction': [],
        'rate_difference': []
    },
    'notes': ["Test partial payment memo entry"],
    'mode': 'Part'
}
            part_memo = check_status_and_return_class(MemoEntry.insert(part_input, get_cls=True))
            cleanup_list.append(part_memo)
            part_memo = MemoEntry.retrieve(test_supplier_id, test_party_id, TEST_MEMO_NUMBER1)
            part_memo_id = part_memo.get_id()
            og_report = make_report({'report': 'khata_report', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            report = TestKhataReport('khata_report', [test_party_id], [test_supplier_id], BILL_DATE, BILL_DATE)
            report_data = report.generate_table([register_entry], [part_memo])
            try:
                assert og_report == report_data
            except AssertionError:
                print('\nDifference in part memo khata report:')
                print_dict_diff(og_report, report_data)
                raise
            og_payment_report = make_report({'report': 'payment_list', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            reference = {'title': 'Payment List', 'from': BILL_DATE, 'to': BILL_DATE, 'headings': [{'title': f'Party Name: {TEST_PARTY_NAME}', 'subheadings': [{'title': f'Supplier Name: {TEST_SUPPLIER_NAME}', 'dataRows': [{'part_no': TEST_MEMO_NUMBER1, 'part_date': format_date_for_display(MEMO_DATE), 'part_amt': '1,250', 'bill_no': int(TEST_BILL_NUMBER), 'bill_amt': '5,000', 'bill_date': format_date_for_display(BILL_DATE), 'pending_amt': 5000, 'days': DAYS_SINCE_BILL, 'status': 'N'}], 'specialRows': [{'name': 'Total (=)', 'value': '1,250', 'column': 'part_amt', 'numeric': 1250, 'beforeData': False}, {'name': '<60 days (+)', 'value': '0', 'column': 'bill_amt', 'numeric': 0, 'beforeData': False}, {'name': '60-120 days (+)', 'value': '0', 'column': 'bill_amt', 'numeric': 0, 'beforeData': False}, {'name': '>120 days (+)', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}, {'name': 'Subtotal (=)', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}, {'name': 'Part (-)', 'value': '- 1,250', 'column': 'bill_amt', 'numeric': 1250, 'beforeData': False}, {'name': 'Pending (=)', 'value': '3,750', 'column': 'bill_amt', 'numeric': 3750, 'beforeData': False}], 'displayOnIndex': True, 'cumulative': {'name': 'Total Pending', 'value': '3,750'}}], 'cumulative': {'name': 'Total Pending', 'value': '3,750'}}]}
            try:
                assert og_payment_report == reference
            except AssertionError:
                print('Difference in Payment List Report')
                print_dict_diff(og_payment_report, reference)
                raise
            gr_amount = 300
            deduction = 300
            # Split the existing deduction into the three new fields
            discount = 100
            rate_difference = 100
            other_deduction = deduction - discount - rate_difference  # Ensure they sum to the original deduction
            part = quarter_pending
            amount = total_pending_amount - part - deduction - gr_amount
            full_input = {
                'memo_number': TEST_MEMO_NUMBER2, 
                'register_date': MEMO_DATE, 
                'amount': amount,
                'gr_amount': gr_amount, 
                'deduction': deduction,  # Keep the original deduction value
                'discount': discount,
                'other_deduction': other_deduction,
                'rate_difference': rate_difference,
                'party_id': test_party_id, 
                'supplier_id': test_supplier_id, 
                'selected_bills': pending_bills, 
                'selected_part': [part_memo_id], 
                'payment': [{'bank': 'RTGS', 'id': 1, 'cheque': '34', 'amount': amount}],  # Add amount to payment
                'less_details': {
                    'gr_amount': ["Note: GR deduction | Amount: " + str(gr_amount)],
                    'discount': ["Note: Cash discount | Amount: " + str(discount)],
                    'other_deduction': ["Note: Miscellaneous deduction | Amount: " + str(other_deduction)],
                    'rate_difference': ["Note: Rate adjustment | Amount: " + str(rate_difference)]
                },
                'notes': ["Test full payment memo with all deduction types"],
                'mode': 'Full'
            }
            full_memo = check_status_and_return_class(MemoEntry.insert(full_input, get_cls=True))
            cleanup_list.append(full_memo)
            full_memo = MemoEntry.retrieve(test_supplier_id, test_party_id, TEST_MEMO_NUMBER2)
            register_entry = RegisterEntry.retrieve(register_entry.supplier_id, register_entry.party_id, register_entry.bill_number, register_entry.register_date)
            print('Creating final khata report')
            og_report = make_report({'report': 'khata_report', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            report = TestKhataReport('khata_report', [test_party_id], [test_supplier_id], BILL_DATE, BILL_DATE)
            report_data = report.generate_table([register_entry], [full_memo])
            try:
                assert og_report == report_data
            except AssertionError:
                print('\nDifference in final khata report:')
                print_dict_diff(og_report, report_data)
                raise
            og_report = make_report({'report': 'supplier_register', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            reference = {'title': 'Supplier Register', 'from': BILL_DATE, 'to': BILL_DATE, 'headings': [{'title': f'Supplier Name: {TEST_SUPPLIER_NAME}', 'subheadings': [{'title': '', 'dataRows': [{'bill_date': format_date_for_display(BILL_DATE), 'party_name': TEST_PARTY_NAME, 'bill_no': int(TEST_BILL_NUMBER), 'bill_amt': '5,000', 'pending_amt': '0', 'status': 'F'}], 'specialRows': [{'name': 'Total (=) ', 'value': '5,000', 'column': 'bill_amt', 'numeric': 5000, 'beforeData': False}, {'name': 'Pending (=) ', 'value': '0', 'column': 'pending_amt', 'numeric': 0, 'beforeData': False}], 'displayOnIndex': False}]}]}
            try:
                assert og_report == reference
            except AssertionError:
                print('Difference in Supplier Register Report')
                print_dict_diff(og_report, reference)
                raise
            og_payment_report = make_report({'report': 'payment_list', 'suppliers': json.dumps([{'id': test_supplier_id}]), 'parties': json.dumps([{'id': test_party_id}]), 'from': BILL_DATE, 'to': BILL_DATE})
            try:
                assert len(og_payment_report['headings']) == 0
            except AssertionError:
                print('\nDifference in empty payment list report:')
                print_dict_diff(og_payment_report['headings'], {'headings': []})
                raise
            print('All Tests Passed')
            cleanup(cleanup_list)
        except Exception as e:
            cleanup(cleanup_list)
            raise e
if __name__ == '__main__':
    run_basic_test()

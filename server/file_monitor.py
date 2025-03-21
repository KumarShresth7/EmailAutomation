import time
import openpyxl
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import json
from datetime import datetime, timedelta
from order_handling import process_order_details, process_order_change
from email_config.emailContentExtract import extract_email_details
from email_config.email_check import suspicious_email_check
from email_config.email_classification import classify_email
from feedback.feedback_handle import process_complaint
from file_processing import process_attachment

excel_file_path = os.path.abspath(r'C:\Users\vedan\Downloads\EmailAutomation\server\Sample.xlsx')
directory_to_watch = os.path.dirname(excel_file_path)

previous_content = []

def read_excel_file():
    content = []
    try:
        wb = openpyxl.load_workbook(excel_file_path)
        sheet = wb.active

        headers = [cell.value for cell in sheet[1]]
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if isinstance(row, tuple):
                if all(cell is None or cell == '' for cell in row):
                    continue
                
                email_data = dict(zip(headers, row)) 
                content.append(email_data)
        return content

    except Exception as e:
        print(f"Error reading the Excel file: {e}")

def compare_changes(new_content):
    global previous_content
    changes = []
    base_timestamp = datetime.now()
    prev_content_tuples = [tuple(row.items()) for row in previous_content if isinstance(row, dict)]
    
    for index, row in enumerate(new_content):
        if not isinstance(row, dict):
            continue  
        row_tuple = tuple(row.items())
        if row_tuple not in prev_content_tuples:
            row_with_timestamp = row.copy()
            current_time = base_timestamp + timedelta(seconds=index)
            row_with_timestamp['Date'] = current_time.strftime("%Y-%m-%d")
            row_with_timestamp['Time'] = current_time.strftime("%H:%M:%S")
            changes.append(row_with_timestamp)
    
    previous_content = new_content.copy()
    return changes

def handle_modified_file():
    new_content = read_excel_file()
    
    if not new_content:
        return
    
    changes = compare_changes(new_content)
    changes_file = "changes.json"
    
    try:
        if changes:
            with open(changes_file, 'w') as f:
                json.dump(changes, f, indent=4)
            
            for change in changes:
                email = change.get("Email")
                body = change.get("Body")
                date = change.get('Date')
                time = change.get('Time')
                attachment_path = change.get('Attachment')
                
                email_status = suspicious_email_check(email)
                is_valid, status = email_status
                
                if is_valid:
                    structured_data = None
                    if attachment_path and os.path.exists(attachment_path):
                        print(f"Processing email with attachment: {attachment_path}")
                        structured_data = process_attachment(attachment_path, body, email, date, time)
                    
                    if structured_data and structured_data.get('orders'):
                        print("Successfully extracted order details from combined email and attachment")
                        process_order_details(email, date, time, structured_data)
                    else:
                        print("No valid structured data from attachment, processing email body only")
                        email_type, email_type_status = classify_email(body)
                        if email_type_status == 200:
                            if email_type == "Order confirmation":
                                order_details = extract_email_details(body)
                                if order_details:
                                    process_order_details(email, date, time, order_details)
                                else:
                                    print("No order details extracted from Order email.")
                            
                            elif email_type == "Change to order":
                                order_details = extract_email_details(body)
                                if order_details:
                                    process_order_change(email, date, time, order_details)
                                else:
                                    print("No order details extracted from Change of Order email.")
                            
                            elif email_type == "Complaint":
                                process_complaint(email, body, date, time)
                        else:
                            print(f"Failed to classify email. Status: {email_type_status}")
                else:
                    print('❌ Email is NOT valid - Status:', status)
                    if status == "Suspicious":
                        print("⚠️ Warning: This email is flagged as suspicious.")
                    elif status == "Exception":
                        print("❗ Error: There was an issue validating the email.")
                    else:
                        print("ℹ️ Email is invalid or not recognized.")
    finally:
        if os.path.exists(changes_file):
            os.remove(changes_file)

def start_monitoring():
    class ExcelFileHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path == excel_file_path:
                print(f"Detected update in file: {excel_file_path}")
                read_excel_file()
                handle_modified_file()
    event_handler = ExcelFileHandler()
    observer = Observer()
    observer.schedule(event_handler, directory_to_watch, recursive=False)
    observer.start()
    print(f"Monitoring updates in {excel_file_path}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("Stopped monitoring.")
    except OSError as e:
        if hasattr(e, 'winerror') and e.winerror == 10038:
            print("Socket error detected. Restarting monitoring...")
            observer.stop()
            time.sleep(1)
            start_monitoring()
        else:
            raise
    finally:
        observer.join()
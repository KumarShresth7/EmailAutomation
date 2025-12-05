import time
import imaplib
import email
from email.header import decode_header
import os
import sys
import threading
from datetime import datetime
from dotenv import load_dotenv
import shutil

# Add server directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from email_config.emailContentExtract import extract_email_details
from order_handling import process_order_details, process_order_change
from email_config.email_check import suspicious_email_check
from email_config.email_classification import classify_email
from feedback.feedback_handle import process_complaint
from file_processing import process_attachment

load_dotenv()

EMAIL_USER = os.getenv("SENDER_EMAIL")
EMAIL_PASS = os.getenv("SENDER_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
ATTACHMENT_DIR = "attachments"

if not os.path.exists(ATTACHMENT_DIR):
    os.makedirs(ATTACHMENT_DIR)

def clean_text(text):
    return "".join(c for c in text if c.isprintable())

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return part.get_payload(decode=True).decode()
    else:
        return msg.get_payload(decode=True).decode()
    return ""

def process_new_emails():
    try:
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Search for all Unseen emails
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if email_ids:
            print(f"\n[IMAP] Found {len(email_ids)} new emails. Processing...")

        for email_id in email_ids:
            try:
                # Fetch the email
                res, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode Subject
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # Decode Sender
                        from_ = msg.get("From")
                        print(f"\n[Processing] From: {from_} | Subject: {subject}")

                        # Get Body
                        body = get_email_body(msg)
                        if not body: 
                            print("  -> Skipping: Empty body")
                            continue

                        # Handle Attachments
                        attachment_path = None
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue
                                
                            filename = part.get_filename()
                            if filename:
                                filepath = os.path.join(ATTACHMENT_DIR, clean_text(filename))
                                with open(filepath, 'wb') as f:
                                    f.write(part.get_payload(decode=True))
                                attachment_path = filepath
                                print(f"  -> Attachment saved: {filename}")

                        # 1. Suspicious Check (Gemini) [PDF Flow]
                        print("  -> Running Suspicious Check...")
                        is_safe, status_msg = suspicious_email_check(body, from_)
                        
                        if not is_safe:
                            print(f"  -> 🛑 DISCARDED: {status_msg}")
                            # Optionally move to Trash here
                            continue

                        # 2. Classification (Gemini)
                        print("  -> Classifying Email...")
                        email_type, status_code = classify_email(body)
                        print(f"  -> Type: {email_type}")

                        date = datetime.now().strftime("%Y-%m-%d")
                        time_str = datetime.now().strftime("%H:%M:%S")

                        # 3. Routing Logic
                        if attachment_path:
                            # Handle attachment-based orders (OCR path from PDF)
                            print("  -> Processing Attachment via OCR...")
                            structured_data = process_attachment(attachment_path, body, from_, date, time_str)
                            if structured_data and structured_data.get('orders'):
                                process_order_details(from_, date, time_str, structured_data)
                        
                        elif email_type == "New Order":
                            print("  -> Extracting New Order Details...")
                            order_details = extract_email_details(body)
                            if order_details:
                                process_order_details(from_, date, time_str, order_details)
                                
                        elif email_type == "Update Order":
                            print("  -> Processing Order Update...")
                            order_details = extract_email_details(body)
                            if order_details:
                                process_order_change(from_, date, time_str, order_details)
                                
                        elif email_type == "Feedback":
                            print("  -> Processing Feedback...")
                            process_complaint(from_, body, date, time_str)
                        
                        else:
                            print(f"  -> Unhandled category: {email_type}")
            except Exception as e:
                print(f"Error processing individual email {email_id}: {e}")

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"Error in IMAP Monitor: {e}")

def start_monitoring():
    print("--- 📧 Email Automation Service Started (IMAP Mode) ---")
    while True:
        process_new_emails()
        time.sleep(10)  # Poll every 10 seconds
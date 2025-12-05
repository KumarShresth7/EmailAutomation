import time
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime
from dotenv import load_dotenv
from email_config.emailContentExtract import extract_email_details
from email_config.email_check import suspicious_email_check
from email_config.email_classification import classify_email
from feedback.feedback_handle import process_complaint
from file_processing import process_attachment

load_dotenv()
EMAIL_USER = os.getenv("SENDER_EMAIL")
EMAIL_PASS = os.getenv("SENDER_PASSWORD")
ATTACHMENT_DIR = "attachments"
if not os.path.exists(ATTACHMENT_DIR): os.makedirs(ATTACHMENT_DIR)

def process_new_emails():
    # Import here to avoid circular dependency
    from order_handling import process_order_details, process_order_change
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        _, messages = mail.search(None, 'UNSEEN')
        for email_id in messages[0].split():
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes): subject = subject.decode()
            sender = msg.get("From")
            print(f"Processing: {subject} from {sender}")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            # Attachments
            att_path = None
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart': continue
                if part.get('Content-Disposition') is None: continue
                filename = part.get_filename()
                if filename:
                    att_path = os.path.join(ATTACHMENT_DIR, filename)
                    with open(att_path, 'wb') as f: f.write(part.get_payload(decode=True))

            # Logic Pipeline
            is_safe, _ = suspicious_email_check(body, sender)
            if not is_safe: continue

            category, _ = classify_email(body)
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")

            if att_path:
                data = process_attachment(att_path, body, sender, date_str, time_str)
                if data.get('orders'): process_order_details(sender, date_str, time_str, data)
            elif category == "New Order":
                data = extract_email_details(body)
                process_order_details(sender, date_str, time_str, data)
            elif category == "Update Order":
                data = extract_email_details(body)
                process_order_change(sender, date_str, time_str, data)
            elif category == "Feedback":
                process_complaint(sender, body, date_str, time_str)

        mail.logout()
    except Exception as e:
        print(f"Monitor Error: {e}")

def start_monitoring():
    while True:
        process_new_emails()
        time.sleep(10)
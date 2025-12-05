import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
from payment.generate_invoice import generate_invoice
from payment.stripe_payment import create_payment_link
from config.dbConfig import db
from bson import ObjectId

load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

def send_email(subject, body, recipient_email, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path:
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_path)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        print(f"📧 Sent to {recipient_email}")
    except Exception as e:
        print(f"❌ Send Error: {e}")

def send_acknowledgment(order, message="", customer_subject=""):
    subject = customer_subject if customer_subject else "Order Confirmation"
    body = f"Hello {order.get('name')},\n\nYour order is received.\n\n{message}\n\nThanks,\nOrderMate Team"
    send_email(subject, body, order['email'])

def send_order_update_confirmation(email, latest_order, previous_order):
    body = "Your order has been updated successfully."
    send_email("Order Updated", body, email)

def send_order_issue_email(email, errors):
    body = f"Issues with your order:\n" + "\n".join(errors)
    send_email("Action Required: Order Issue", body, email)

def send_invoice(order_id):
    order = db['orders'].find_one({"_id": ObjectId(order_id)})
    if not order: return

    invoice_path = generate_invoice(order)
    payment_link = create_payment_link(order_id)
    
    body = f"Your order is ready. Pay here: {payment_link}"
    send_email("Invoice & Payment", body, order['email'], invoice_path)
    
    if os.path.exists(invoice_path): os.remove(invoice_path)
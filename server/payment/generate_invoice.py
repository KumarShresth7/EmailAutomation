from fpdf import FPDF
import datetime

def generate_invoice(order):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Invoice for Order {order['_id']}", ln=1, align="C")
    
    for item in order.get('products', []):
        pdf.cell(200, 10, txt=f"{item['name']} - Qty: {item['quantity']}", ln=1)
        
    filename = f"invoice_{order['_id']}.pdf"
    pdf.output(filename)
    return filename
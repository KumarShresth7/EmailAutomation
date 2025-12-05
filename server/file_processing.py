import pymupdf as fitz
import easyocr
import pandas as pd
import json
import os
import re
from config.gemini_config import gemini_model

# Initialize OCR reader (downloads model on first run)
reader = easyocr.Reader(['en'])

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def extract_data_from_excel(excel_path):
    try:
        df = pd.read_excel(excel_path)
        return df.to_json(orient="records")
    except Exception as e:
        print(f"Error extracting Excel: {e}")
        return ""

def extract_text_from_image(image_path):
    try:
        text = reader.readtext(image_path, detail=0)
        return " ".join(text).strip()
    except Exception as e:
        print(f"Error extracting Image: {e}")
        return ""

def send_to_gemini(data, email, date, time):
    prompt = f"""
    Extract structured order details from this text.
    
    Data:
    {data}
    
    Context:
    Sender Email: {email}
    Date: {date}
    
    Return JSON:
    {{
        "customer": {{ "name": "", "email": "{email}", "phone": "", "address": "" }},
        "orders": [ {{ "product": "exact product name", "quantity": 0 }} ]
    }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        return {}

def process_attachment(attachment_path, email_body, email, date, time):
    if not attachment_path or not os.path.exists(attachment_path):
        return None
    
    extracted_data = ""
    if attachment_path.endswith(".pdf"):
        extracted_data = extract_text_from_pdf(attachment_path)
    elif attachment_path.endswith((".xlsx", ".xls", ".csv")):
        extracted_data = extract_data_from_excel(attachment_path)
    elif attachment_path.endswith((".jpg", ".jpeg", ".png")):
        extracted_data = extract_text_from_image(attachment_path)
    
    combined_text = f"Email Body: {email_body}\nAttachment Content: {extracted_data}"
    return send_to_gemini(combined_text, email, date, time)
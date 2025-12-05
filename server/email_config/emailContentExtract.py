import json
from config.gemini_config import gemini_model
import re

def extract_email_details(email_text):
    prompt = f"""
    You are an AI data extractor. Extract customer and order details from the email below.

    **Email:**
    "{email_text}"

    **Rules:**
    1. Return JSON ONLY.
    2. If customer details (name/phone/address) are missing, use null.
    3. Standardize product names where possible.

    **Expected JSON Structure:**
    {{
        "customer": {{
            "name": "Full Name",
            "email": "email@address.com",
            "phone": "1234567890",
            "address": "Full Address"
        }},
        "orders": [
            {{"product": "Product Name", "quantity": 10}}
        ]
    }}
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        
        clean_text = re.sub(r"```json|```", "", text).strip()
        data = json.loads(clean_text)
        
        return {
            "customer": data.get("customer"),
            "orders": data.get("orders")
        }
    except Exception as e:
        print(f"Extraction Error: {e}")
        return {"customer": None, "orders": None}
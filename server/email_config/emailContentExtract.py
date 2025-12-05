from config.gemini_config import gemini_model
import json

def extract_email_details(email_text):
    prompt = f"""
    Extract customer and order data.
    Email: "{email_text}"
    Return JSON:
    {{
        "customer": {{ "name": "", "email": "", "phone": "", "address": "" }},
        "orders": [ {{ "product": "", "quantity": 0 }} ]
    }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return {"customer": None, "orders": None}
from config.gemini_config import gemini_model
from config.dbConfig import db
import json

def get_urgent_restocking():
    inventory = list(db["inventory"].find({}, {"_id": 0, "name": 1, "quantity": 1}))
    prompt = f"""
    Identify items needing urgent restocking (stock < 10).
    Data: {json.dumps(inventory)}
    Return JSON: {{ "urgent_restocking": [ {{ "product": "", "current_stock": 0, "recommended_stock": 50 }} ] }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return {"urgent_restocking": []}
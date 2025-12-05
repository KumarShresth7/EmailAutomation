from config.gemini_config import gemini_model
from config.dbConfig import db
import json

def identify_deadstocks():
    inventory = list(db["inventory"].find({}, {"_id": 0, "name": 1, "quantity": 1}))
    # Mocking sales data aggregation for simplicity, or query orders
    prompt = f"""
    Analyze this inventory for deadstock (high stock, low implied sales).
    Inventory: {json.dumps(inventory)}
    Return JSON: {{ "deadstocks": [ {{ "name": "", "inventory": 0, "sales": 0 }} ] }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.replace("```json", "").replace("```", "").strip())
    except:
        return {"deadstocks": []}
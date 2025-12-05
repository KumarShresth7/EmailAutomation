from config.gemini_config import gemini_model
import json

def classify_email(body):
    prompt = f"""
    Classify email into: "New Order", "Update Order", "Feedback", or "Other".
    Body: "{body[:500]}"
    Return JSON: {{ "label": "CategoryName" }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        return data.get("label", "Other"), 200
    except:
        return "Other", 500
from config.gemini_config import gemini_model
import json

def suspicious_email_check(email_body, sender_email):
    prompt = f"""
    Analyze if this email is suspicious (phishing, spam, malicious).
    Sender: {sender_email}
    Body: "{email_body[:500]}"
    
    Return JSON: {{ "is_safe": boolean, "reason": "short explanation" }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        return data.get("is_safe", True), data.get("reason", "Checked")
    except Exception as e:
        print(f"Check Error: {e}")
        return True, "Check Failed (Default Safe)"
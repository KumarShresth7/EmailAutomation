from config.gemini_config import gemini_model
from config.dbConfig import db
from datetime import datetime
import json

error_collection = db["errors"]

def suspicious_email_check(email_body, sender_email):
    """
    Uses Gemini to analyze email context for phishing or malicious intent.
    This replaces the simple ZeroBounce check with semantic analysis.
    """
    try:
        prompt = f"""
        Analyze this email for suspicious activity (phishing, scams, malicious links).
        
        Sender: {sender_email}
        Body: "{email_body[:1000]}"

        Return JSON:
        {{
            "is_safe": true/false,
            "reason": "Short explanation"
        }}
        """
        
        response = gemini_model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        
        is_safe = result.get("is_safe", False)
        reason = result.get("reason", "Unknown")
        
        return is_safe, reason if not is_safe else "Safe"
        
    except Exception as e:
        print(f"Security Check Error: {e}")
        # Log error but fail open (allow email) or closed depending on preference
        error_data = {
            "errorMessage": f"AI Security Check Failed: {str(e)}",
            "type": "System",
            "severity": "Medium",
            "timestamp": datetime.utcnow()
        }
        error_collection.insert_one(error_data)
        return True, "AI Check Failed (Default Safe)"
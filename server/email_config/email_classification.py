import json
import re
from config.gemini_config import gemini_model

def classify_email(body):
    try:
        prompt = f"""
        You are an intelligent email classifier for an order management system.
        Classify the following email into exactly one of these categories:
        - "New Order" (customer placing a new order)
        - "Update Order" (customer modifying an existing order, changing quantity, etc.)
        - "Feedback" (complaints, reviews, or general feedback)
        - "Other" (spam, promotions, or irrelevant)

        **Email Content:**
        "{body[:2000]}"  # Truncate to avoid token limits

        **Output Format:**
        Return JSON only: {{"label": "Category Name"}}
        """

        response = gemini_model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown if present
        if "```" in text:
            text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)
        label_map = {
            "New Order": "New Order",
            "Update Order": "Update Order",
            "Feedback": "Feedback"
        }
        
        # Normalize the label
        api_label = data.get("label", "Other")
        final_label = label_map.get(api_label, "Other")
        
        return final_label, 200

    except Exception as e:
        print(f"Classification Error: {e}")
        return "Other", 500
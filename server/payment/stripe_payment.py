import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_payment_link(order_id):
    # Simplified mock link for robustness if Stripe fails
    try:
        # Real logic would create a session here
        return f"https://checkout.stripe.com/pay/{order_id}" 
    except:
        return "https://stripe.com/error"
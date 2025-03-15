from ai21 import AI21Client
from ai21.models.chat import UserMessage
import json
from config.dbConfig import db
from datetime import datetime, timedelta
from send_email import send_acknowledgment, send_order_update_confirmation, send_order_issue_email
import os
from dotenv import load_dotenv
from config.gemini_config import gemini_model
import re
from pymongo import DESCENDING

load_dotenv()
API_KEY = os.getenv("AI21KEY")

client = AI21Client(api_key=API_KEY)
order_collection = db['orders']
inventory_collection = db['inventory']
customers_collection = db['customers']

def fetch_inventory_items():
    inventory_items = inventory_collection.find({}, {"_id": 0, "name": 1})
    return {item["name"] for item in inventory_items}

def correct_product_names(order_details, inventory_items):
    try:
        inventory_list = "\n".join(inventory_items)
        orders_list = "\n".join([f"- {order['product']}" for order in order_details])
        
        prompt = f"""
        Here is our inventory list:
        {inventory_list}

        And here are the ordered products:
        {orders_list}

        For each ordered product, find the closest matching product from our inventory.
        Return only the corrected product names, one per line.
        """

        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()

        corrected_product_names = [name.lstrip("- ").strip() for name in ai_response.split("\n") if name.strip()]

        corrected_orders = []
        for i, order in enumerate(order_details):
            if i < len(corrected_product_names):
                corrected_orders.append({
                    "product": corrected_product_names[i],
                    "quantity": order["quantity"]
                })
            else:
                corrected_orders.append(order)

    except Exception as e:
        print(f"Error correcting product names: {e}")
        corrected_orders = order_details

    print('Corrected Orders:', corrected_orders)
    return corrected_orders

def validate_order_details_ai(order_details):
    prompt = f"""
    You are an AI assistant validating order details.
    Your task is to check if the order contains incomplete, incorrect, or unclear details.

    **Validation Criteria:**
    - Ensure that each item has a product name and quantity.
    - The price is not required.
    - If any required detail is missing or unclear, list it as an error.

    **Order Details:**
    {json.dumps(order_details, indent=2)}

    **Expected JSON Output (Strict Format, No Explanation):**
    {{
        "valid": true/false,
        "errors": ["Missing quantity for product X"]
    }}
    """

    try:
        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()

        clean_response = re.sub(r"```json|```", "", ai_response).strip()

        try:
            validation_result = json.loads(clean_response)
            return validation_result.get("valid", False), validation_result.get("errors", [])
        except json.JSONDecodeError as e:
            return False, [f"Invalid AI response format. JSON Parsing Error: {str(e)}"]

    except Exception as e:
        return False, [f"System error while validating order: {str(e)}"]

def extract_order_details_ai(email_text):
    """
    Extracts structured order details from an email using AI21.
    Returns a list of products and quantities.
    """
    messages = [
        UserMessage(
            content=f"""
            You are an AI assistant extracting order details from an email.
            Extract and return only in JSON format:

            **Email:**
            "{email_text}"

            **Expected JSON Output:**
            {{
                "orders": [
                    {{"product": "Product Name", "quantity": Number}}
                ]
            }}
            """
        )
    ]
    try:
        response = client.chat.completions.create(
            model="jamba-1.5-large",
            messages=messages,
            top_p=1.0
        )
        result = response.model_dump()
        
        if "choices" in result and result["choices"]:
            content_str = result["choices"][0]["message"]["content"]
            extracted_orders = json.loads(content_str)
            return extracted_orders.get("orders", [])
        else:
            print("Error: No choices found in API response.")
            return []
    except Exception as e:
        print(f"Error extracting order details: {e}")
        return []

def check_inventory(order_details):
    for order in order_details:
        product = order["product"]
        quantity = order["quantity"]

        inventory_item = inventory_collection.find_one({"item": product})
        if not inventory_item or inventory_item["quantity"] < quantity:
            return False

    return True

def get_customer_from_db(email):
    return customers_collection.find_one({"email": email})

def add_orders_to_collection(email, date, time, customer_details, order_details):
    inventory_items = fetch_inventory_items()
    corrected_orders = correct_product_names(order_details, inventory_items)
    unknown_products = [
        order["product"] for order in corrected_orders if order["product"] not in inventory_items
    ]

    if unknown_products:
        print('Unknown products found. Order not added.')
        # send_order_issue_email( #TODO: Send customized msg
        #     email, [f"The following products are not in our inventory: {', '.join(unknown_products)}"]
        # )
        return None
    
    order_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")

    existing_order = order_collection.find_one(
        {
            "email": email,
            "products": corrected_orders,
            "date": {"$gte": (order_datetime - timedelta(minutes=5)).strftime("%Y-%m-%d")},
            "time": {"$gte": (order_datetime - timedelta(minutes=5)).strftime("%H:%M:%S")}
        }
    )

    if existing_order:
        print("Duplicate entry detected. Order not added.")
        return

    can_fulfill = check_inventory(order_details=corrected_orders)

    formatted_entry = {
        "name": customer_details['name'],
        "phone": customer_details['phone'],
        "email": email,
        "date": date,
        "time": time,
        "products": [{"name": item["product"], "quantity": item["quantity"]} for item in corrected_orders],
        "status": "pending fulfillment",
        "orderLink": ""
    } #TODO: Update the inventory after order is added
    order_collection.insert_one(formatted_entry)
    print('Order added to collection.')
    send_acknowledgment(formatted_entry)

def process_order_details(email, date, time, order_details):
    customer_details = order_details.get("customer", None)
    print('Customer Details: ',customer_details)
    orders = order_details.get("orders", None)

    if not orders:
        print("No order details found in email.")
        send_order_issue_email(email, ["No order details were found in your email. Please send a valid order."])
        return

    is_valid, errors = validate_order_details_ai(orders)

    if not is_valid:
        print("Order details are invalid. Sending issue email.")
        # send_order_issue_email(email, errors)
        return

    existing_customer = get_customer_from_db(email)

    if existing_customer:
        if not customer_details or not all(k in customer_details for k in ["name", "email", "phone"]):
            customer_details = {
                "name": existing_customer.get("name", ""),
                "email": existing_customer.get("email", ""),
                "phone": existing_customer.get("phone", ""),
                "address": existing_customer.get("address", "")
            }
        
        if all(customer_details.values()):
            print("Customer details are complete. Proceeding with order processing.")
            order_id = add_orders_to_collection(email, date, time, customer_details, orders)

            if order_id:
                customers_collection.update_one(
                    {"email": email},
                    {"$push": {"past_orders": order_id}}
                )
        else:
            print("Customer details are incomplete. Sending issue email.")
            send_order_issue_email(email, ["Your customer details are incomplete. Please update your information."])
    else:
        if customer_details and all(k in customer_details for k in ["name", "email", "phone", "address"]):
            print("New customer detected. Creating customer entry in the database.")

            new_customer = {
                "name": customer_details["name"],
                "email": customer_details["email"],
                "phone": customer_details["phone"],
                "address": customer_details["address"],
                "past_orders": [],
                "created_at": datetime.utcnow()
            }
            customer_id = customers_collection.insert_one(new_customer).inserted_id

            print("New customer added to database. Proceeding with order processing.")
            order_id = add_orders_to_collection(email, date, time, customer_details, orders)

            if order_id:
                customers_collection.update_one(
                    {"_id": customer_id},
                    {"$push": {"past_orders": order_id}}
                )

        else:
            print("Customer details are incomplete. Sending issue email.")
            send_order_issue_email(email, [
                "We could not find your details in our system, and the provided details are incomplete."
                "Please provide your name, email, phone, and address to create an account and process your order."
            ])

def process_order_change(email, date, time, order_details):
    print('Processing order change...')
    try:
        latest_order = order_collection.find_one({"email": email}, sort=[("date", DESCENDING), ("time", DESCENDING)])
        if not latest_order:
            process_order_details(email, date, time, order_details)
            return

        if latest_order.get("status") not in ["pending fulfillment", "partially fulfilled"]:
            process_order_details(email, date, time, order_details)
            return
        
        updated_products = get_ai_order_updates(latest_order, order_details)
        
        order_collection.update_one(
            {"_id": latest_order["_id"]},
            {"$set": {"products": updated_products}}
        )
        
        updated_order = order_collection.find_one({"_id": latest_order["_id"]})
        send_order_update_confirmation(email, updated_order)
    
    except Exception as e:
        print(f"Error updating order: {e}")
        send_order_issue_email(email, ["An error occurred while updating your order."])

def get_ai_order_updates(previous_order, new_order_details):
    """
    Use AI to intelligently merge the previous order with the new order details.
    Handles cases of adding new items, modifying quantities, and removing items.
    """
    try:
        previous_products = previous_order.get("products", [])
        previous_products_formatted = json.dumps(previous_products, indent=2)
        
        new_products = new_order_details.get("orders", [])
        new_products_formatted = json.dumps(new_products, indent=2)
        
        prompt = f"""
        You are an AI assistant helping with order updates.
        
        PREVIOUS ORDER:
        {previous_products_formatted}
        
        REQUESTED CHANGES:
        {new_products_formatted}
        
        Analyze these changes and determine the appropriate action for each item:
        1. If an item in the requested changes already exists in the previous order, update its quantity accordingly.
        2. If an item in the requested changes doesn't exist in the previous order, add it as a new item.
        3. If the requested changes specify a quantity of 0 for an existing item, remove it from the order.
        4. If an item in the previous order isn't mentioned in the requested changes, keep it unchanged.
        
        Return ONLY a valid JSON array of the updated products in this exact format:
        [
            {{"name": "Product Name", "quantity": Number}}
        ]
        """
        
        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()
        
        clean_response = re.sub(r"``````", "", ai_response).strip()
        
        try:
            updated_products = json.loads(clean_response)
            return updated_products
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            return merge_orders_fallback(previous_order, new_order_details)
            
    except Exception as e:
        print(f"Error in AI order update: {e}")
        return merge_orders_fallback(previous_order, new_order_details)

def merge_orders_fallback(previous_order, new_order_details):
    """
    Fallback method to merge orders if AI processing fails.
    Simply adds new quantities to existing items or adds new items.
    """
    existing_products = {item["name"]: item["quantity"] for item in previous_order.get("products", [])}
    
    for new_item in new_order_details.get("orders", []):
        product_name = new_item["product"]
        quantity = new_item["quantity"]
        
        if quantity == 0 and product_name in existing_products:
            del existing_products[product_name]
        elif product_name in existing_products:
            existing_products[product_name] = quantity
        else:
            existing_products[product_name] = quantity

    return [{"name": name, "quantity": qty} for name, qty in existing_products.items()]

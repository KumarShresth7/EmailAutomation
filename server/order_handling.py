import json
from config.dbConfig import db
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from email_config.send_emails import send_acknowledgment, send_order_update_confirmation, send_order_issue_email
from config.gemini_config import gemini_model
import re
from pymongo import DESCENDING
from error_handle import handle_exception

load_dotenv()

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
        handle_exception(e)
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
            return False, [f"Invalid AI response format: {str(e)}"]

    except Exception as e:
        return False, [f"System error while validating order: {str(e)}"]

def extract_order_details_ai(email_text):
    """
    Updated to use Gemini instead of AI21
    """
    prompt = f"""
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
    try:
        response = gemini_model.generate_content(prompt)
        result = response.text.strip()
        clean_result = re.sub(r"```json|```", "", result).strip()
        
        extracted_data = json.loads(clean_result)
        return extracted_data.get("orders", [])
            
    except Exception as e:
        handle_exception(e)
        print(f"Error extracting order details: {e}")
        return []

def check_inventory(order_details):
    for order in order_details:
        product = order["product"]
        quantity = order["quantity"]

        inventory_item = inventory_collection.find_one({"name": product})
        if not inventory_item or inventory_item["quantity"] < quantity:
            return False
    return True

def get_customer_from_db(email):
    return customers_collection.find_one({"email": email})

def add_orders_to_collection(email, date, time, customer_details, order_details):
    try:
        inventory_items = fetch_inventory_items()
        corrected_orders = correct_product_names(order_details, inventory_items)
        unknown_products = [
            order["product"] for order in corrected_orders if order["product"] not in inventory_items
        ]

        if unknown_products:
            print('Unknown products found. Order not added.')
            return None
        
        order_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        twenty_four_hours_ago = order_datetime - timedelta(hours=24)
        yesterday_date = twenty_four_hours_ago.strftime("%Y-%m-%d")
        yesterday_time = twenty_four_hours_ago.strftime("%H:%M:%S")

        existing_order = order_collection.find_one({
            "email": email,
            "$or": [
                {"date": date, "time": {"$gte": yesterday_time, "$lte": time}} if date == yesterday_date else {"date": date},
                {"date": yesterday_date, "time": {"$gte": yesterday_time}} if date != yesterday_date else {}
            ],
            "products": {
                "$size": len(corrected_orders),
                "$all": [
                    {"$elemMatch": {
                        "name": item["product"],
                        "quantity": item["quantity"]
                    }} for item in corrected_orders
                ]}
        })

        if existing_order:
            print("Duplicate order detected. Order not added.")
            send_order_issue_email(email, ["A duplicate order was detected within the last few minutes."])
            return None

        # Check Inventory
        can_fulfill = check_inventory(order_details=corrected_orders)
        status = "pending fulfillment" if can_fulfill else "pending inventory"
        
        formatted_entry = {
            "name": customer_details.get('name', 'Unknown'),
            "phone": customer_details.get('phone', ''),
            "email": email,
            "date": date,
            "time": time,
            "products": [{"name": item["product"], "quantity": item["quantity"]} for item in corrected_orders],
            "status": status,
            "orderLink": ""
        }
        
        result = order_collection.insert_one(formatted_entry)
        order_id = str(result.inserted_id)
        
        order_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"orderLink": f"http://localhost:3000/track-order/{order_id}"}}
        )
        
        if can_fulfill:
            # Deduct inventory
            for item in corrected_orders:
                inventory_collection.update_one(
                    {"name": item["product"]},
                    {"$inc": {"quantity": -item["quantity"]}}
                )
            send_acknowledgment(formatted_entry)
        else:
             send_acknowledgment(formatted_entry, message="Some items are currently out of stock...", customer_subject="Order Update")

        return order_id
            
    except Exception as e:
        print(f"Unexpected error in add_orders_to_collection: {e}")
        handle_exception(e)
        return None

def validate_customer_details_ai(email, customer_details):
    try:
        if not customer_details:
            customer_details = {}
            
        prompt = f"""
        You are an AI assistant validating customer details.
        Validation Criteria:
        - Required fields: name, email, phone, address
        - Each field should have a non-empty value
        - If any required field is missing/empty, list it as missing

        **Customer Details:**
        {json.dumps(customer_details, indent=2)}

        **Output:**
        {{
            "valid": true/false,
            "missing_fields": ["field1", "field2"]
        }}
        """

        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()
        clean_response = re.sub(r"```json|```", "", ai_response).strip()

        try:
            validation_result = json.loads(clean_response)
            return validation_result.get("valid", False), validation_result.get("missing_fields", []), customer_details
        except json.JSONDecodeError as e:
            return False, ["Error validating customer details"], customer_details

    except Exception as e:
        handle_exception(e)
        return False, ["System error"], customer_details

def process_order_details(email, date, time, order_details):
    customer_details = order_details.get("customer", None)
    orders = order_details.get("orders", None)

    if not orders:
        print("No order details found in email.")
        send_order_issue_email(email, ["No order details were found in your email."])
        return

    is_valid, errors = validate_order_details_ai(orders)
    if not is_valid:
        return

    existing_customer = get_customer_from_db(email)
    customer_id = None

    if not existing_customer:
        is_valid, missing_fields, customer_details = validate_customer_details_ai(email, customer_details)
        if not is_valid:
            error_message = [f"Missing details: {', '.join(missing_fields)}."]
            send_order_issue_email(email, error_message)
            return
        
        new_customer = {
            "name": customer_details["name"],
            "email": customer_details["email"],
            "phone": customer_details["phone"],
            "address": customer_details["address"],
            "past_orders": [],
            "created_at": datetime.utcnow()
        }
        result = customers_collection.insert_one(new_customer)
        customer_id = result.inserted_id
    else:
        customer_id = existing_customer["_id"]
        # Logic to update customer details if missing could go here

    order_id = add_orders_to_collection(email, date, time, customer_details, orders)
    
    if order_id:
        order_summary = {
            "order_id": order_id,
            "date": date,
            "time": time,
            "products": orders,
            "status": "pending fulfillment"
        }
        customers_collection.update_one(
            {"_id": customer_id},
            {"$push": {"past_orders": order_summary}}
        )

def process_order_change(email, date, time, order_details):
    try:
        latest_order = order_collection.find_one({"email": email}, sort=[("date", DESCENDING), ("time", DESCENDING)])
        if not latest_order:
            process_order_details(email, date, time, order_details)
            return

        if latest_order.get("status") not in ["pending fulfillment", "partially fulfilled"]:
            process_order_details(email, date, time, order_details)
            return
        
        previous_order = {
            "_id": latest_order["_id"],
            "products": latest_order["products"].copy(),
            "date": latest_order["date"],
            "time": latest_order["time"]
        }
        
        updated_products = get_ai_order_updates(latest_order, order_details)
        
        order_collection.update_one(
            {"_id": latest_order["_id"]},
            {"$set": {"products": updated_products}}
        )
        
        updated_order = order_collection.find_one({"_id": latest_order["_id"]})
        send_order_update_confirmation(email, latest_order=updated_order, previous_order=previous_order)
    
    except Exception as e:
        handle_exception(e)
        print(f"Error updating order: {e}")

def get_ai_order_updates(previous_order, new_order_details):
    try:
        previous_products = previous_order.get("products", [])
        new_products = new_order_details.get("orders", [])
        
        prompt = f"""
        You are an AI assistant helping with order updates.
        
        PREVIOUS ORDER:
        {json.dumps(previous_products)}
        
        REQUESTED CHANGES:
        {json.dumps(new_products)}
        
        Analyze changes:
        1. If item exists, update quantity.
        2. If item is new, add it.
        3. If quantity is 0, remove it.
        
        Return JSON array: [{{"name": "Product Name", "quantity": Number}}]
        """
        
        response = gemini_model.generate_content(prompt)
        ai_response = response.text.strip()
        clean_response = re.sub(r"```json|```", "", ai_response).strip()
        
        return json.loads(clean_response)
            
    except Exception as e:
        handle_exception(e)
        return []
import json
from config.dbConfig import db
from email_config.send_emails import send_acknowledgment
from config.gemini_config import gemini_model

def correct_product_names(orders):
    inventory = [i['name'] for i in db['inventory'].find({}, {"name": 1})]
    prompt = f"Inventory: {inventory}\nOrders: {orders}\nMatch orders to inventory names. Return JSON list of {{'product': 'name', 'quantity': qty}}"
    res = gemini_model.generate_content(prompt)
    try:
        return json.loads(res.text.replace("```json", "").replace("```", ""))
    except:
        return orders

def process_order_details(email, date, time, data):
    raw_orders = data.get("orders", [])
    if not raw_orders: return
    
    orders = correct_product_names(raw_orders)
    customer = data.get("customer", {})
    
    # Check Inventory
    can_fulfill = True
    for o in orders:
        item = db['inventory'].find_one({"name": o['product']})
        if not item or item['quantity'] < o['quantity']:
            can_fulfill = False
            break
            
    order_doc = {
        "email": email, "name": customer.get("name"), "date": date, "time": time,
        "products": [{"name": o['product'], "quantity": o['quantity']} for o in orders],
        "status": "pending fulfillment" if can_fulfill else "pending inventory"
    }
    
    res = db['orders'].insert_one(order_doc)
    db['orders'].update_one({"_id": res.inserted_id}, {"$set": {"orderLink": f"http://localhost:3000/track-order/{res.inserted_id}"}})
    
    if can_fulfill:
        for o in orders:
            db['inventory'].update_one({"name": o['product']}, {"$inc": {"quantity": -o['quantity']}})
            
    send_acknowledgment(order_doc)

def process_order_change(email, date, time, data):
    # Implementation for updating orders
    pass
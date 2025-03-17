from flask import Flask, jsonify, request # type: ignore
import threading
from file_monitor import start_monitoring
from config.dbConfig import db
from feedback_handle import fetch_feedback, store_feedback
from chatbot import ask_bot
from flask_cors import CORS
from bson.objectid import ObjectId
from analytics.deadstock import identify_deadstocks
from analytics.dynamicPricing import generate_pricing_suggestions
from analytics.urgentRestock import get_urgent_restocking
from werkzeug.exceptions import HTTPException
from send_email import send_invoice
import json

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

app = Flask(__name__)
app.json_encoder = JSONEncoder
CORS(app, resources={
    r"/*": {
        "origins": "*"
    }
})

def start_monitoring_thread():
    if not any(thread.name == "FileMonitorThread" for thread in threading.enumerate()):
        thread = threading.Thread(target=start_monitoring, daemon=True, name="FileMonitorThread")
        thread.start()

start_monitoring_thread()

@app.route('/')
def index():
    return 'File Monitoring is Already Running!', 200

@app.route('/get-feedback')
def get_feedback():
    try:
        feedback_data = fetch_feedback()
        response = store_feedback(feedback_data)
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chatbot', methods=['POST'])
def chat():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    
    response = ask_bot(query)
    return jsonify({"response": response})

@app.route('/orders/<order_id>', methods=['GET'])
def get_order_info(order_id):
    try:
        if not ObjectId.is_valid(order_id):
            return jsonify({"error": "Invalid order ID"}), 400

        order_collection = db['orders']
        order = order_collection.find_one({"_id": ObjectId(order_id)})

        if not order:
            return jsonify({"error": "Order not found"}), 404

        order_data = {
            "id": str(order["_id"]),
            "name": order.get("name", ""),
            "phone": order.get("phone", ""),
            "email": order.get("email", ""),
            "date": order.get("date", ""),
            "time": order.get("time", ""),
            "products": order.get("products", []),
            "status": order.get("status", ""),
            "orderLink": order.get("orderLink", "")
        }

        return jsonify(order_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

#? Analytics Endpoints
@app.route('/analytics/deadstocks', methods=['GET'])
def get_deadstocks():
    deadstock_list = identify_deadstocks()
    return jsonify(deadstock_list)

@app.route('/analytics/dynamic_pricing', methods=['GET'])
def price_summary():
    summary = generate_pricing_suggestions()
    return jsonify({"Pricing Suggestions": summary})

@app.route('/analytics/urgent-restocking', methods=['GET'])
def urgent_restocking():
    restocking_data = get_urgent_restocking()
    return jsonify(restocking_data)

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

#? CRUD Endpoints
@app.route('/get-orders', methods=['GET'])
def get_orders():
    orders_collection = db['orders']
    orders = list(orders_collection.find({}, {'_id': 0}))
    return jsonify(orders), 200

@app.route('/update-status', methods=['PUT', 'OPTIONS'])
def handle_status_update():
    if request.method == 'OPTIONS':
        return '', 200
        
    data = request.get_json()
    order_id = data.get('orderId')
    new_status = data.get('status')
    
    if not order_id or not new_status:
        return jsonify({"error": "Order ID and status are required"}), 400
        
    orders_collection = db['orders']
    result = orders_collection.update_one(
        {"orderLink": order_id},
        {"$set": {"status": new_status}}
    )
    
    if result.modified_count == 0:
        return jsonify({"error": "Order not found or status not changed"}), 404
    
    if new_status == "fulfilled":
        send_invoice(order_id)
        
    return jsonify({"success": True, "message": "Order status updated successfully"}), 200

@app.route('/get-inventory')
def get_inventory():
    try:
        inventory_collection = db['inventory']
        inventory_items = list(inventory_collection.find({}, {}))
        
        for item in inventory_items:
            item['_id'] = str(item['_id'])
        
        return jsonify(inventory_items), 200
    except Exception as e:
        print(f"Error retrieving inventory: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-inventory/<item_id>', methods=['GET'])
def get_inventory_item(item_id):
    try:
        inventory_collection = db['inventory']
        item = inventory_collection.find_one({"_id": ObjectId(item_id)})
        if not item:
            return jsonify({"error": "Item not found"}), 404
            
        item['_id'] = str(item['_id'])
        return jsonify(item), 200
    except Exception as e:
        print(f"Error retrieving item: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/add-inventory', methods=['POST'])
def add_inventory():
    try:
        inventory_collection = db['inventory']
        data = request.json
        
        required_fields = ['name', 'category', 'price', 'quantity', 'warehouse_location', 'stock_alert_level']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = inventory_collection.insert_one(data)
        
        new_item = data
        new_item['_id'] = str(result.inserted_id)
        
        return jsonify(new_item), 201
    except Exception as e:
        print(f"Error adding inventory item: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update-inventory/<item_id>', methods=['PUT'])
def update_inventory(item_id):
    try:
        inventory_collection = db['inventory']
        data = request.json
        
        if '_id' in data:
            del data['_id']
        
        result = inventory_collection.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Item not found"}), 404
            
        updated_item = inventory_collection.find_one({"_id": ObjectId(item_id)})
        updated_item['_id'] = str(updated_item['_id'])
        
        return jsonify(updated_item), 200
    except Exception as e:
        print(f"Error updating inventory item: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/delete-inventory/<item_id>', methods=['DELETE'])
def delete_inventory(item_id):
    try:
        inventory_collection = db['inventory']
        result = inventory_collection.delete_one({"_id": ObjectId(item_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
        
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting inventory item: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug=True)
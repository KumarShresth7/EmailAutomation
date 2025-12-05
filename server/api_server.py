from flask import Flask, jsonify, request, session
import uuid
import os
from flask_cors import CORS
from bson import ObjectId
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import json

# --- Import Core Modules ---
from config.dbConfig import db
from feedback.feedback_handle import fetch_feedback, store_feedback
from chatbot import ask_bot, refresh_data_and_update_vector_store, store_chat_history, get_chat_history
from analytics.deadstock import identify_deadstocks
from analytics.dynamicPricing import generate_pricing_suggestions
from analytics.urgentRestock import get_urgent_restocking
from email_config.send_emails import send_invoice
from payment.stripe_payment import create_payment_link
from error_handle import handle_exception

# --- JSON Encoder for MongoDB ---
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

# --- Configuration ---
load_dotenv()
app = Flask(__name__)
app.json_encoder = JSONEncoder
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# --- Middleware ---
@app.before_request
def before_request():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

# --- Basic Route ---
@app.route('/')
def index():
    return '🚀 OrderMate Dashboard API is Running!', 200

# ==========================================
#  CHATBOT ROUTES
# ==========================================

@app.route('/chatbot', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Query parameter is required"}), 400

        query = data['query']
        session_id = session.get('session_id', str(uuid.uuid4()))
        
        # Get response from RAG Chatbot
        response_data = ask_bot(query, session_id)
        response_text = response_data.get('response', '')
        
        if response_text:
            store_chat_history(session_id, query, response_text)
            
        return jsonify({"response": response_text, "session_id": session_id})
    except Exception as e:
        print(f"Chat Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat-history', methods=['GET'])
def get_session_chat_history_route():
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({"error": "No active session"}), 400
            
        limit = int(request.args.get("limit", 10))
        history = get_chat_history(session_id, limit)
        return jsonify({"history": history, "session_id": session_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/end-session', methods=['POST'])
def end_session():
    session.pop('session_id', None)
    return jsonify({"message": "Session ended"})

@app.route('/refresh-data', methods=['POST'])
def refresh_data():
    try:
        refresh_data_and_update_vector_store()
        return jsonify({"message": "Knowledge base refreshed successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
#  ANALYTICS ROUTES
# ==========================================

@app.route('/product-analytics', methods=['GET'])
def get_product_analytics():
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # 1. Best Selling
        pipeline_best = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$unwind": "$products"},
            {"$group": {"_id": "$products.name", "quantity": {"$sum": "$products.quantity"}}},
            {"$sort": {"quantity": -1}},
            {"$limit": 5}
        ]
        best_selling = list(db['orders'].aggregate(pipeline_best))
        
        # 2. Worst Selling
        pipeline_worst = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$unwind": "$products"},
            {"$group": {"_id": "$products.name", "quantity": {"$sum": "$products.quantity"}}},
            {"$sort": {"quantity": 1}},
            {"$limit": 5}
        ]
        worst_selling = list(db['orders'].aggregate(pipeline_worst))
        
        # 3. Revenue
        pipeline_revenue = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$addFields": {
                "total_amount": {"$sum": {"$map": {
                    "input": "$products",
                    "as": "product",
                    "in": {"$multiply": [{"$ifNull": ["$$product.price", 0]}, "$$product.quantity"]}
                }}}
            }},
            {"$group": {"_id": "$date", "revenue": {"$sum": "$total_amount"}}},
            {"$sort": {"_id": 1}}
        ]
        revenue_per_day = list(db['orders'].aggregate(pipeline_revenue))
        
        # 4. Feedback
        recent_feedback = list(db['feedback'].find().sort("createdAt", -1).limit(5))
        
        return jsonify({
            'productSales': {
                'bestSelling': [{'name': i['_id'], 'quantity': i['quantity']} for i in best_selling],
                'worstSelling': [{'name': i['_id'], 'quantity': i['quantity']} for i in worst_selling]
            },
            'revenuePerDay': [{'date': i['_id'], 'revenue': i['revenue']} for i in revenue_per_day],
            'customerFeedback': [{
                'name': i.get('email', 'Anonymous'),
                'feedback': i.get('review', ''),
                'sentiment': i.get('type', 'neutral')
            } for i in recent_feedback]
        })
    except Exception as e:
        print(f"Product Analytics Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/customer-analytics', methods=['GET'])
def get_customer_analytics():
    try:
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        pipeline_trends = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$group": {"_id": "$date", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        order_trends = list(db['orders'].aggregate(pipeline_trends))
        
        pipeline_frequent = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$group": {"_id": "$name", "order_count": {"$sum": 1}}},
            {"$sort": {"order_count": -1}},
            {"$limit": 10}
        ]
        frequent_customers = list(db['orders'].aggregate(pipeline_frequent))
        
        pipeline_spenders = [
            {"$match": {"date": {"$gte": thirty_days_ago.strftime('%Y-%m-%d')}}},
            {"$unwind": "$products"},
            {"$addFields": {
                "item_total": {"$multiply": [{"$ifNull": ["$products.price", 0]}, "$products.quantity"]}
            }},
            {"$group": {
                "_id": "$name", 
                "total_spent": {"$sum": "$item_total"}
            }},
            {"$sort": {"total_spent": -1}},
            {"$limit": 10}
        ]
        top_spenders = list(db['orders'].aggregate(pipeline_spenders))
        
        return jsonify({
            'orderTrends': {
                'dates': [i['_id'] for i in order_trends],
                'counts': [i['count'] for i in order_trends]
            },
            'frequentCustomers': {
                'names': [i['_id'] for i in frequent_customers],
                'counts': [i['order_count'] for i in frequent_customers]
            },
            'topSpenders': {
                'names': [i['_id'] for i in top_spenders],
                'amounts': [i['total_spent'] for i in top_spenders]
            }
        })
    except Exception as e:
        print(f"Customer Analytics Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/analytics/deadstocks', methods=['GET'])
def get_deadstocks_route():
    return jsonify(identify_deadstocks())

@app.route('/analytics/dynamic_pricing', methods=['GET'])
def get_pricing_route():
    return jsonify({"Pricing Suggestions": generate_pricing_suggestions()})

@app.route('/analytics/urgent-restocking', methods=['GET'])
def get_restocking_route():
    return jsonify(get_urgent_restocking())

# ==========================================
#  ORDER & INVENTORY ROUTES
# ==========================================

@app.route('/get-orders', methods=['GET'])
def get_orders():
    try:
        orders = list(db['orders'].find({}).sort([('date', -1), ('time', -1)]))
        for order in orders:
            order['_id'] = str(order['_id'])
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/orders/<order_id>', methods=['GET'])
def get_order_info(order_id):
    try:
        if not ObjectId.is_valid(order_id):
            return jsonify({"error": "Invalid ID"}), 400
        order = db['orders'].find_one({"_id": ObjectId(order_id)})
        if not order:
            return jsonify({"error": "Not Found"}), 404
        order['_id'] = str(order['_id'])
        return jsonify(order), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-status', methods=['PUT', 'OPTIONS'])
def update_status():
    if request.method == 'OPTIONS': return '', 200
    try:
        data = request.get_json()
        order_id = data.get('orderId')
        new_status = data.get('status')
        
        result = db['orders'].update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"status": new_status}}
        )
        
        if result.modified_count > 0 and new_status.lower() == "fulfilled":
            try:
                send_invoice(order_id=order_id)
            except Exception as e:
                print(f"Invoice sending failed: {e}")
                
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-inventory', methods=['GET'])
def get_inventory():
    try:
        items = list(db['inventory'].find({}, {}))
        for item in items:
            item['_id'] = str(item['_id'])
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-inventory/<item_id>', methods=['GET'])
def get_inventory_item(item_id):
    try:
        item = db['inventory'].find_one({"_id": ObjectId(item_id)})
        if item:
            item['_id'] = str(item['_id'])
            return jsonify(item), 200
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/add-inventory', methods=['POST'])
def add_inventory():
    try:
        data = request.json
        result = db['inventory'].insert_one(data)
        data['_id'] = str(result.inserted_id)
        return jsonify(data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-inventory/<item_id>', methods=['PUT'])
def update_inventory(item_id):
    try:
        data = request.json
        if '_id' in data: del data['_id']
        db['inventory'].update_one({"_id": ObjectId(item_id)}, {"$set": data})
        updated = db['inventory'].find_one({"_id": ObjectId(item_id)})
        updated['_id'] = str(updated['_id'])
        return jsonify(updated), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-inventory/<item_id>', methods=['DELETE'])
def delete_inventory(item_id):
    try:
        result = db['inventory'].delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Not found"}), 404
        return jsonify({"message": "Deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/create-payment-link/<order_id>", methods=["GET"])
def get_payment_link(order_id):
    try:
        link = create_payment_link(order_id)
        return jsonify({"payment_link": link})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
#  FEEDBACK & ERRORS
# ==========================================

@app.route('/get-feedback', methods=['GET'])
def get_feedback():
    try:
        # Fetch external feedback if configured
        # data = fetch_feedback()
        # store_feedback(data)
        
        feedbacks = list(db['feedback'].find({}, {"_id": 0}))
        return jsonify({"feedbacks": feedbacks}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/errors', methods=['GET'])
def get_errors():
    try:
        errors = list(db['errors'].find({}, {'_id': 0}))
        return jsonify({"errors": errors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
#  ERROR HANDLER & STARTUP
# ==========================================

@app.errorhandler(Exception)
def global_error_handler(e):
    return handle_exception(e)

if __name__ == '__main__':
    # Initialize Scheduler for RAG updates
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_data_and_update_vector_store, 'interval', hours=1)
    scheduler.start()
    
    print("---------------------------------------------------")
    print("   🚀 DASHBOARD & CHATBOT SERVER STARTED")
    print("   Running on port 5000")
    print("---------------------------------------------------")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
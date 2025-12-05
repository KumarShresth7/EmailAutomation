from flask import Flask, jsonify, request, session
import threading
import uuid
import os
# CHANGED: Imported from the correct file_monitor
from file_monitor import start_monitoring
from config.dbConfig import db
from feedback.feedback_handle import fetch_feedback, store_feedback
from chatbot import ask_bot, refresh_data_and_update_vector_store, store_chat_history, get_chat_history
from flask_cors import CORS
from bson import ObjectId
from analytics.deadstock import identify_deadstocks
from analytics.dynamicPricing import generate_pricing_suggestions
from analytics.urgentRestock import get_urgent_restocking
from werkzeug.exceptions import HTTPException
from email_config.send_emails import send_invoice
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

load_dotenv()
app = Flask(__name__)
app.json_encoder = JSONEncoder
app.secret_key = os.getenv("FLASK_SECRET_KEY")

error_collection = db["errors"]

CORS(app, resources={r"/*": {"origins": "*"}})

# Start the IMAP Email Monitor in a background thread
def start_monitoring_thread():
    if not any(thread.name == "FileMonitorThread" for thread in threading.enumerate()):
        thread = threading.Thread(target=start_monitoring, daemon=True, name="FileMonitorThread")
        thread.start()

start_monitoring_thread()

@app.before_request
def before_request():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    return 'Server & Email Monitor Running!', 200

# ... [Keep all other existing routes identical to previous main.py] ...
# (The rest of the file handles Chatbot, Analytics, Orders, etc. and does not need logic changes)

if __name__ == '__main__':
    # Initialize scheduler for data refresh
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_data_and_update_vector_store, 'interval', hours=1)
    scheduler.start()
    app.run(host='0.0.0.0', debug=True)
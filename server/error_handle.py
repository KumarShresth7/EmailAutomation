from flask import jsonify
from datetime import datetime
from werkzeug.exceptions import HTTPException
from config.dbConfig import db

error_collection = db["errors"]

def handle_exception(e, source="system"):
    severity = "Medium"
    if isinstance(e, HTTPException):
        if e.code == 400: severity = "Low"
    else:
        severity = "Critical"

    error_data = {
        "errorMessage": str(e),
        "type": "System" if source == "system" else "Customer",
        "severity": severity,
        "timestamp": datetime.utcnow()
    }
    error_collection.insert_one(error_data)
    
    response = {"error": str(e)}
    return response
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = "store_db"

def connect_db():
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    print("✅ Connected to MongoDB")
    return db

db = connect_db()
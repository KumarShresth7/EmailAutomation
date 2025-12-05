import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain.schema import Document
from google.cloud import aiplatform
from langchain_google_vertexai import VertexAIEmbeddings
import pandas as pd
from config.gemini_config import gemini_model
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config.dbConfig import db

load_dotenv()
inventory_collection = db["inventory"]
feedback_collection = db["feedback"]
orders_collection = db["orders"]
customers_collection = db["customers"]
chat_history_collection = db["chat_history"]

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\Deloitte\Prototype\server\services\fresh-airfoil-445517-q1-89b2bc080318.json"
aiplatform.init(project=PROJECT_ID, location="us-central1")
embeddings = VertexAIEmbeddings(model="text-embedding-004", project=PROJECT_ID)

def load_collection_data(collection):
    try:
        return list(collection.find({}, {"_id": 0}))
    except Exception as e:
        print(f"Error loading from collection: {e}")
        return []

def store_chat_history(session_id, query, response):
    """Store chat interactions in MongoDB using session ID"""
    chat_history_collection.insert_one({
        "session_id": session_id,
        "query": query,
        "response": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

def get_chat_history(session_id, limit=10):
    """Retrieve chat history for a specific session"""
    history = list(chat_history_collection.find(
        {"session_id": session_id}, 
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit))
    
    return history

def build_records_from_collection(data, collection_name):
    records = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    for idx, record in enumerate(data):
        text = str(record)
        chunks = text_splitter.split_text(text)
        for chunk_idx, chunk in enumerate(chunks):
            if not chunk or chunk.strip() == "":
                continue
                
            records.append({
                "id": f"{collection_name}{idx}_chunk{chunk_idx}",
                "text": chunk,
                "source": collection_name,
                "record_type": collection_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    return records

vector_store = Chroma(
    collection_name="customer",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

def upsert_documents(new_docs):
    if not vector_store:
        print("❌ Error: Vector store is not initialized.")
        return

    try:
        existing_docs = vector_store.get()
        existing_ids = set(existing_docs["ids"]) if existing_docs and "ids" in existing_docs else set()

        new_filtered_docs = [doc for doc in new_docs if doc.metadata["id"] not in existing_ids]

        if new_filtered_docs:
            vector_store.add_documents(new_filtered_docs)
            print(f"✅ Added {len(new_filtered_docs)} new documents to vector store.")
        else:
            print("⚠ No new documents to add.")
    except Exception as e:
        print("❌ Error during upsert:", e)

def build_documents(records):
    docs = []
    for rec in records:
        metadata = {
            "id": rec["id"],
            "source": rec["source"],
            "record_type": rec.get("record_type", "general"),
            "timestamp": rec["timestamp"],
            "priority": "high" if rec["source"] in ["app_docs", "technical_docs"] else "normal"
        }
        docs.append(Document(
            page_content=rec["text"],
            metadata=metadata
        ))
    return docs

def refresh_data_and_update_vector_store():
    customers = load_collection_data(customers_collection)
    inventory = load_collection_data(inventory_collection)
    orders = load_collection_data(orders_collection)
    feedback = load_collection_data(feedback_collection)

    all_records = (
        build_records_from_collection(customers, "customers") +
        build_records_from_collection(inventory, "inventory") +
        build_records_from_collection(orders, "orders") +
        build_records_from_collection(feedback, "feedback")
    )

    docs = build_documents(all_records)
    upsert_documents(docs)
    
    return vector_store

def extract_keywords(text):
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                    'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'like', 'from'}
    
    words = text.lower().split()
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    return keywords

def calculate_metadata_relevance(metadata, query):
    """Calculate how relevant metadata is to query"""
    query_lower = query.lower()
    score = 0
    
    if "source" in metadata:
        if metadata["source"].lower() == "inventory" and ("inventory" in query_lower or 
                                                          "stock" in query_lower or 
                                                          "product" in query_lower):
            score += 0.5
        elif metadata["source"].lower() == "orders" and ("order" in query_lower or 
                                                        "purchase" in query_lower or 
                                                        "buy" in query_lower):
            score += 0.5
    
    return score

def retrieve_similar_docs(query, k=15):
    if vector_store is None:
        return []
    
    try:
        results = vector_store.similarity_search_with_score(query, k=k*2)
        
        keywords = extract_keywords(query)
        
        reranked_results = []
        for doc, score in results:
            keyword_score = sum(1 for keyword in keywords if keyword.lower() in doc.page_content.lower())
            
            metadata_score = calculate_metadata_relevance(doc.metadata, query)
            
            recency_score = 0
            if "timestamp" in doc.metadata:
                try:
                    doc_time = datetime.fromisoformat(doc.metadata["timestamp"])
                    time_diff = (datetime.now(timezone.utc) - doc_time).days
                    recency_score = max(0, 1 - (time_diff / 30))
                except:
                    pass
            
            final_score = (
                (1 - score) * 0.5 +
                keyword_score * 0.2 +
                metadata_score * 0.2 +
                recency_score * 0.1
            )
            
            reranked_results.append((doc, final_score))
        
        sorted_results = sorted(reranked_results, key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in sorted_results[:k]]
    
    except Exception as e:
        print(f"❌ Error retrieving similar docs: {e}")
        return []

def ask_bot(query, session_id=None):
    history_text = ""
    if session_id:
        chat_history = get_chat_history(session_id)
        if chat_history:
            history_text = "Previous conversation:\n"
            for entry in reversed(chat_history):
                history_text += f"User: {entry['query']}\nAssistant: {entry['response']}\n\n"
    
    relevant_docs = retrieve_similar_docs(query, k=100)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])
    
    prompt = f"""
You are an AI assistant with expertise in:
- *Order Management*
- *Inventory Tracking*
- *Product Analytics*

Use the *provided context and chat history* to answer the query accurately.

*Chat History:*
{history_text}

*Context:*
{context}

*Query:*
{query}

*Instructions:*
1. If the context contains relevant *order, inventory, or analytics* information, answer directly.
2. If missing details, *explain what additional info is needed*.
3. Reference previous conversations when relevant.

*Answer:*
"""
    
    response = gemini_model.generate_content(prompt)
    response_text = response.text.strip() if hasattr(response, "text") else ""
    
    if response and hasattr(response, "text"):
        return {"response": response_text}
    else:
        return {"error": "Invalid response format from Google Vertex AI"}

refresh_data_and_update_vector_store()

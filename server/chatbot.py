import os
import chromadb
from datetime import datetime, timezone
import google.generativeai as genai
from config.gemini_config import gemini_model
from config.dbConfig import db

chroma_client = chromadb.PersistentClient(path="./chroma_native_db")
collection = chroma_client.get_or_create_collection("customer_data")

def get_embedding(text):
    return genai.embed_content(model="models/text-embedding-004", content=text)['embedding']

def chunk_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size-50)]

def refresh_data_and_update_vector_store():
    print("Refreshing RAG...")
    docs, ids, embs = [], [], []
    
    for col_name in ["customers", "inventory", "orders", "feedback"]:
        data = list(db[col_name].find({}, {"_id": 0}))
        for i, item in enumerate(data):
            chunks = chunk_text(str(item))
            for j, chunk in enumerate(chunks):
                ids.append(f"{col_name}_{i}_{j}")
                docs.append(chunk)
                embs.append(get_embedding(chunk))
    
    if ids:
        collection.upsert(ids=ids, documents=docs, embeddings=embs)

def ask_bot(query, session_id):
    # 1. Retrieve
    q_emb = get_embedding(query)
    results = collection.query(query_embeddings=[q_emb], n_results=5)
    context = "\n".join(results['documents'][0])
    
    # 2. History
    history = list(db['chat_history'].find({"session_id": session_id}).sort("timestamp", -1).limit(5))
    hist_text = "\n".join([f"U: {h['query']}\nA: {h['response']}" for h in reversed(history)])

    # 3. Generate
    prompt = f"Context:\n{context}\n\nHistory:\n{hist_text}\n\nUser: {query}\nAnswer:"
    res = gemini_model.generate_content(prompt)
    return {"response": res.text.strip()}

def store_chat_history(sid, q, r):
    db['chat_history'].insert_one({"session_id": sid, "query": q, "response": r, "timestamp": datetime.now().isoformat()})

def get_chat_history(sid, limit):
    return list(db['chat_history'].find({"session_id": sid}, {"_id": 0}).limit(limit))
from config.dbConfig import db

def generate_pricing_suggestions():
    inventory = list(db["inventory"].find())
    suggestions = []
    
    for item in inventory:
        stock = item.get("quantity", 0)
        price = item.get("price", 0)
        name = item.get("name")
        
        new_price = price
        if stock > 100: new_price = price * 0.90 # Discount excess
        elif stock < 10: new_price = price * 1.10 # Premium scarcity
        
        if new_price != price:
            suggestions.append({"Product": name, "Old Price": price, "New Price": round(new_price, 2)})
            
    return {"pricing_recommendations": suggestions}
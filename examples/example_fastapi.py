"""
Example demonstrating the use of satya with FastAPI.

This example shows how to:
1. Define satya models for responses
2. Use satya models with FastAPI
3. Return satya models from FastAPI endpoints
4. Use SatyaJSONResponse for custom response handling
"""
from typing import List, Optional, Dict, Any
import uvicorn
from pydantic import BaseModel

from fastapi import FastAPI, Body

from satya import Model, Field
from satya.fastapi import SatyaJSONResponse, validate_request_model

# Define satya models for responses
class Item(Model):
    id: int = Field(ge=1, description="The item ID")
    name: str = Field(min_length=1, max_length=50, description="The item name")
    description: Optional[str] = Field(required=False, description="The item description")
    price: float = Field(gt=0, description="The item price")
    is_offer: bool = Field(description="Whether the item is on offer")
    tags: List[str] = Field(description="Tags for the item")

# Define Pydantic models for requests (FastAPI requirement)
class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float 
    is_offer: bool = False
    tags: List[str] = []
    
class ItemQuery(BaseModel):
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    tag: Optional[str] = None

# Create a standard FastAPI application
app = FastAPI(title="Satya FastAPI Example", version="0.1.0")

# Basic route with path parameter
@app.get("/")
def read_root():
    return {"message": "Welcome to Satya FastAPI Example!"}

# Use SatyaJSONResponse to handle satya models in responses
@app.post("/items/", response_class=SatyaJSONResponse)
def create_item(item: ItemCreate):
    """
    Create a new item.
    
    Uses Pydantic for request validation but returns a satya Model.
    The SatyaJSONResponse handles serializing the satya Model automatically.
    """
    # Convert Pydantic model to dict and create a satya model
    item_dict = item.dict()
    
    # Create a satya model (normally you'd validate business rules, save to DB, etc.)
    satya_item = Item(
        id=123,  # In real app this would be from DB
        name=item_dict["name"],
        description=item_dict["description"],
        price=item_dict["price"],
        is_offer=item_dict["is_offer"],
        tags=item_dict["tags"]
    )
    
    # Return a dict with a nested satya model (SatyaJSONResponse will handle it)
    return {
        "item": satya_item,
        "message": f"Item {item.name} created successfully"
    }

# Regular FastAPI route, just converting to satya model at the end
@app.get("/items/search", response_class=SatyaJSONResponse)
def search_items(query: ItemQuery):
    """
    Search for items with filtering.
    
    Uses Pydantic for request validation but returns satya models.
    """
    # In a real app, you'd search a database
    # For demo, we'll create a mock item based on query params
    
    # Create sample prices list
    prices = [9.99, 19.99, 29.99, 39.99, 49.99]
    
    # Filter prices based on query
    filtered_prices = prices
    if query.min_price is not None:
        filtered_prices = [p for p in filtered_prices if p >= query.min_price]
    if query.max_price is not None:
        filtered_prices = [p for p in filtered_prices if p <= query.max_price]
    
    # Create sample items with filtered prices
    items = []
    for i, price in enumerate(filtered_prices, 1):
        item = Item(
            id=i,
            name=f"Item {i}",
            description=f"Description for item {i}",
            price=price,
            is_offer=price % 20 == 0,  # Every 20.00 is an offer
            tags=["tag1", query.tag] if query.tag else ["tag1"]
        )
        items.append(item)
    
    # Return satya models in a list
    return {"items": items, "count": len(items)}

# Direct satya model response
@app.get("/custom", response_class=SatyaJSONResponse)
def custom_response():
    """
    Endpoint that explicitly returns a satya Model.
    
    This demonstrates how SatyaJSONResponse handles a satya Model directly.
    """
    # Create and return a satya model instance directly
    return Item(
        id=999,
        name="Custom Item",
        description="This is a custom response",
        price=99.99,
        is_offer=True,
        tags=["custom", "special"]
    )

if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run("example_fastapi:app", host="127.0.0.1", port=8000, reload=True)

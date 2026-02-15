from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.db_service import db
import os
import httpx    
router = APIRouter(prefix="/api/customer", tags=["customer"])

# Data models for validation
class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float
    unit_price: float

class CreateOrderRequest(BaseModel):
    customer_phone: str
    items: List[OrderItem]
    is_credit: bool = False

# Endpoint to get products
@router.get("/products/{store_id}")
async def get_products(store_id: str):
    """
    Get all available products
    
    Try it: http://localhost:8002/api/customer/products/your-store-id
    """
    print(f"📦 Getting products for store: {store_id}")
    
    products = db.get_products(store_id)
    
    # Supabase may return relation as "products" or "product"
    product_info_key = "products"  # will try "product" if needed
    formatted_products = []
    for item in products:
        try:
            info = item.get("products") or item.get("product")
            if not info:
                print(f"   [api] row missing products/product. keys={list(item.keys())}")
                continue
            # Handle both list (one-to-many) and dict (many-to-one)
            if isinstance(info, list):
                info = info[0] if info else {}
            formatted_products.append({
                "product_id": str(item.get("product_id", "")),
                "name": info.get("name", ""),
                "description": info.get("description") or "",
                "unit": info.get("unit", "unit"),
                "price": float(item.get("unit_price", 0)),
                "available": float(item.get("quantity", 0))
            })
        except Exception as e:
            print(f"   [api] format error for row: {e}. keys={list(item.keys())}")
    
    print(f"   [api] returning {len(formatted_products)} products")
    
    return {
        "success": True,
        "store_id": store_id,
        "products": formatted_products,
        "count": len(formatted_products)
    }

# Endpoint to place order
@router.post("/order/{store_id}")
async def place_order(store_id: str, order: CreateOrderRequest):
    """
    Place a new order
    
    Send JSON like:
    {
      "customer_phone": "9876543210",
      "items": [
        {
          "product_id": "abc-123",
          "product_name": "Atta",
          "quantity": 2,
          "unit_price": 40
        }
      ],
      "is_credit": false
    }
    """
    print(f"🛒 Placing order for store: {store_id}")
    
    # Get or create customer
    customer = db.get_customer_by_phone(store_id, order.customer_phone)
    if not customer:
        raise HTTPException(status_code=400, detail="Could not create customer")
    
    # Calculate total
    total = sum(item.quantity * item.unit_price for item in order.items)
    
    # Create order
    order_id = db.create_order(
        store_id=store_id,
        customer_id=customer["id"],
        items=[item.dict() for item in order.items],
        total_amount=total,
        is_credit=order.is_credit
    )
    
    if not order_id:
        raise HTTPException(status_code=500, detail="Could not create order")
        # Trigger agent service
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8003/api/events/trigger",
                json={
                    "event_type": "order_created",
                    "store_id": store_id,
                    "payload": {
                        "order_id": order_id,
                        "customer_id": customer["id"],
                        "items": [item.dict() for item in order.items],
                        "is_credit": order.is_credit
                    }
                },
                timeout=5.0
            )
            print("✅ Agent notified")
    except Exception as e:
        print(f"⚠️ Could not notify agent: {e}")
    
    print(f"✅ Order created: {order_id}")
    
    return {
        "success": True,
        "order_id": order_id,
        "customer_name": customer["name"],
        "total_amount": total,
        "message": "Order placed successfully!"
    }
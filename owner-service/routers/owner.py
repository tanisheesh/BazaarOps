from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.db_service import db
import os

router = APIRouter(prefix="/api/owner", tags=["owner"])

# Data models
class InventoryUpdate(BaseModel):
    product_id: str
    quantity: float

class OrderStatusUpdate(BaseModel):
    status: str

# Dashboard endpoint
@router.get("/dashboard/{store_id}")
async def get_dashboard(store_id: str):
    """
    Get dashboard statistics
    
    Returns: today's orders, revenue, low stock items
    """
    print(f"📊 Getting dashboard stats for store: {store_id}")
    
    stats = db.get_dashboard_stats(store_id)
    
    return stats

# Inventory endpoints
@router.get("/inventory/{store_id}")
async def get_inventory(store_id: str):
    """
    Get all inventory for a store
    
    Returns: list of products with stock levels
    """
    print(f"📦 Getting inventory for store: {store_id}")
    
    inventory = db.get_inventory(store_id)
    
    # Format response
    formatted_inventory = []
    for item in inventory:
        product = item.get("products", {})
        category = product.get("categories", {})
        
        formatted_inventory.append({
            "inventory_id": item["id"],
            "product_id": item["product_id"],
            "product_name": product.get("name", "Unknown"),
            "description": product.get("description", ""),
            "category": category.get("name", "Uncategorized"),
            "quantity": float(item["quantity"]),
            "unit": product.get("unit", "piece"),
            "unit_price": float(item["unit_price"]),
            "reorder_threshold": float(item["reorder_threshold"]),
            "status": "low" if float(item["quantity"]) < float(item["reorder_threshold"]) else "ok"
        })
    
    return {
        "success": True,
        "inventory": formatted_inventory,
        "count": len(formatted_inventory)
    }

@router.post("/inventory/{store_id}/update")
async def update_inventory(store_id: str, update: InventoryUpdate):
    """
    Update inventory quantity
    
    Body: {
        "product_id": "abc-123",
        "quantity": 50.5
    }
    """
    print(f"📝 Updating inventory: {update.product_id} to {update.quantity}")
    
    result = db.update_inventory(store_id, update.product_id, update.quantity)
    
    if not result:
        raise HTTPException(status_code=500, detail="Could not update inventory")
    
    return {
        "success": True,
        "message": "Inventory updated",
        "data": result
    }

# Orders endpoints
@router.get("/orders/{store_id}")
async def get_orders(store_id: str, limit: int = 50):
    """
    Get recent orders
    
    Query params: limit (default 50)
    """
    print(f"📋 Getting orders for store: {store_id}")
    
    orders = db.get_orders(store_id, limit)
    
    # Format response
    formatted_orders = []
    for order in orders:
        customer = order.get("customers", {})
        
        formatted_orders.append({
            "order_id": order["id"],
            "customer_name": customer.get("name", "Unknown"),
            "customer_phone": customer.get("phone", ""),
            "total_amount": float(order["total_amount"]),
            "status": order["status"],
            "payment_status": order["payment_status"],
            "created_at": order["created_at"],
            "notes": order.get("notes", "")
        })
    
    return {
        "success": True,
        "orders": formatted_orders,
        "count": len(formatted_orders)
    }

@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, update: OrderStatusUpdate):
    """
    Update order status
    
    Body: {
        "status": "completed"
    }
    
    Valid statuses: pending, confirmed, completed, cancelled
    """
    print(f"📝 Updating order {order_id} to {update.status}")
    
    valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    result = db.update_order_status(order_id, update.status)
    
    if not result:
        raise HTTPException(status_code=500, detail="Could not update order")
    
    return {
        "success": True,
        "message": "Order status updated",
        "data": result
    }

# Customers endpoint
@router.get("/customers/{store_id}")
async def get_customers(store_id: str):
    """Get all customers"""
    print(f"👥 Getting customers for store: {store_id}")
    
    customers = db.get_customers(store_id)
    
    return {
        "success": True,
        "customers": customers,
        "count": len(customers)
    }

# Notification endpoint (for agent service to call)
@router.post("/notify")
async def notify_owner(store_id: str, message: str):
    """
    Receive notification from agent service
    
    Body: {
        "store_id": "abc-123",
        "message": "New order received!"
    }
    """
    print(f"🔔 Notification for store {store_id}: {message}")
    
    # In real implementation, send to Telegram bot
    # For now, just log it
    
    return {
        "success": True,
        "message": "Notification received"
    }


# Customer Telegram endpoint
@router.get("/customer-telegram/{phone}")
async def get_customer_telegram(phone: str):
    """
    Get customer's telegram chat_id by phone number
    """
    try:
        customer = db.supabase.table("customers")\
            .select("telegram_chat_id")\
            .eq("phone", phone)\
            .single()\
            .execute()
        
        if customer.data:
            return {"telegram_chat_id": customer.data.get("telegram_chat_id")}
        else:
            return {"telegram_chat_id": None}
    except Exception as e:
        print(f"❌ Error getting customer telegram: {e}")
        return {"telegram_chat_id": None}

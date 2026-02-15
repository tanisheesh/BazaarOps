from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", "").strip(),
    os.getenv("SUPABASE_KEY", "").strip()
)

class OwnerDatabaseService:
    """Database operations for store owners"""
    
    @staticmethod
    def get_inventory(store_id: str):
        """Get all inventory with product details"""
        try:
            response = supabase.table("inventory")\
                .select("*, products(id, name, description, unit, category_id, categories(name))")\
                .eq("store_id", store_id)\
                .order("products(name)")\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting inventory: {e}")
            return []
    
    @staticmethod
    def update_inventory(store_id: str, product_id: str, quantity: float):
        """Update inventory quantity"""
        try:
            response = supabase.table("inventory")\
                .update({"quantity": quantity, "updated_at": "now()"})\
                .eq("store_id", store_id)\
                .eq("product_id", product_id)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error updating inventory: {e}")
            return None
    
    @staticmethod
    def get_orders(store_id: str, limit: int = 50):
        """Get recent orders"""
        try:
            response = supabase.table("orders")\
                .select("*, customers(name, phone)")\
                .eq("store_id", store_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
            return []
    
    @staticmethod
    def update_order_status(order_id: str, status: str):
        """Update order status"""
        try:
            response = supabase.table("orders")\
                .update({"status": status, "updated_at": "now()"})\
                .eq("id", order_id)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error updating order: {e}")
            return None
    
    @staticmethod
    def get_dashboard_stats(store_id: str):
        """Get dashboard statistics"""
        from datetime import datetime
        
        try:
            today = datetime.now().date()
            
            # Get today's orders with order items and product details in one query
            orders_response = supabase.table("orders")\
                .select("id, total_amount, created_at, status, order_items(quantity, product_id, products(cost_price))")\
                .eq("store_id", store_id)\
                .gte("created_at", today.isoformat())\
                .execute()
            
            total_orders = len(orders_response.data)
            total_revenue = 0
            total_cost = 0
            
            for order in orders_response.data:
                total_revenue += float(order["total_amount"])
                
                # Calculate cost from order items
                if order.get("order_items"):
                    for item in order["order_items"]:
                        quantity = float(item.get("quantity", 0))
                        cost_price = 0
                        
                        if item.get("products") and item["products"].get("cost_price"):
                            cost_price = float(item["products"]["cost_price"])
                        
                        total_cost += cost_price * quantity
            
            total_profit = total_revenue - total_cost
            
            print(f"📊 Revenue: ₹{total_revenue}, Cost: ₹{total_cost}, Profit: ₹{total_profit}")
            
            # Get low stock items
            inventory_response = supabase.table("inventory")\
                .select("quantity, reorder_threshold, products(name)")\
                .eq("store_id", store_id)\
                .execute()
            
            low_stock_items = [
                {
                    "name": item["products"]["name"],
                    "quantity": float(item["quantity"]),
                    "threshold": float(item["reorder_threshold"])
                }
                for item in inventory_response.data
                if float(item["quantity"]) < float(item["reorder_threshold"])
            ]
            
            return {
                "today_orders": total_orders,
                "today_revenue": total_revenue,
                "today_profit": total_profit,
                "low_stock_count": len(low_stock_items),
                "low_stock_items": low_stock_items
            }
        except Exception as e:
            print(f"❌ Error getting dashboard stats: {e}")
            import traceback
            traceback.print_exc()
            return {
                "today_orders": 0,
                "today_revenue": 0,
                "today_profit": 0,
                "low_stock_count": 0,
                "low_stock_items": []
            }
    
    @staticmethod
    def get_customers(store_id: str):
        """Get all customers"""
        try:
            response = supabase.table("customers")\
                .select("*")\
                .eq("store_id", store_id)\
                .order("name")\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting customers: {e}")
            return []

# Create instance
db = OwnerDatabaseService()

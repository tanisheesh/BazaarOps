from supabase import create_client, Client
import os

# Connect to Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class DatabaseService:
    """Handle all database operations"""
    
    @staticmethod
    def get_products(store_id: str):
        """Get all products for a store"""
        try:
            response = supabase.table("inventory")\
                .select("*, products(id, name, description, unit)")\
                .eq("store_id", store_id)\
                .gt("quantity", 0)\
                .execute()
            
            data = response.data or []
            print(f"   [db] get_products store_id={store_id!r} -> {len(data)} rows")
            if data:
                print(f"   [db] first row keys: {list(data[0].keys())}")
            return data
        except Exception as e:
            print(f"❌ Error getting products: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    def create_order(store_id: str, customer_id: str, items: list, 
                    total_amount: float, is_credit: bool):
        """Create a new order"""
        try:
            # Create the order
            order_data = {
                "store_id": store_id,
                "customer_id": customer_id,
                "total_amount": total_amount,
                "status": "confirmed",
                "payment_status": "unpaid" if is_credit else "paid"
            }
            
            order_response = supabase.table("orders")\
                .insert(order_data)\
                .execute()
            
            order_id = order_response.data[0]["id"]
            
            # Create order items
            for item in items:
                item_data = {
                    "order_id": order_id,
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "subtotal": item["quantity"] * item["unit_price"]
                }
                supabase.table("order_items").insert(item_data).execute()
            
            return order_id
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            return None
    
    @staticmethod
    def get_customer_by_phone(store_id: str, phone: str):
        """Find customer by phone or create new one"""
        try:
            # Try to find existing customer
            response = supabase.table("customers")\
                .select("*")\
                .eq("store_id", store_id)\
                .eq("phone", phone)\
                .execute()
            
            if response.data:
                return response.data[0]
            
            # Create new customer if not found
            customer_data = {
                "store_id": store_id,
                "name": f"Customer {phone[-4:]}",
                "phone": phone
            }
            new_response = supabase.table("customers")\
                .insert(customer_data)\
                .execute()
            
            return new_response.data[0]
        except Exception as e:
            print(f"❌ Error with customer: {e}")
            return None

# Create instance to use
db = DatabaseService()
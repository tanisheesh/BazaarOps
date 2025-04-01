from events.event_bus import event_bus, Event
from supabase import create_client
import os

class OrderAgent:
    """Processes orders automatically"""
    
    def __init__(self):
        # Connect to database
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Subscribe to order events
        event_bus.subscribe("order_created", self.handle_order)
        print("✅ Order Agent ready")
    
    async def handle_order(self, event: Event):
        """Process an order"""
        print(f"🛒 Processing order...")
        
        try:
            payload = event.payload
            order_id = payload.get("order_id")
            items = payload.get("items", [])
            
            # Update inventory for each item
            for item in items:
                await self.update_inventory(
                    event.store_id,
                    item["product_id"],
                    item["quantity"]
                )
            
            # Mark order as confirmed
            self.supabase.table("orders")\
                .update({"status": "confirmed"})\
                .eq("id", order_id)\
                .execute()
            
            print(f"✅ Order {order_id[:8]} confirmed")
            
            # Trigger inventory check
            await event_bus.publish(Event(
                type="inventory_updated",
                store_id=event.store_id,
                payload={"order_id": order_id}
            ))
            
        except Exception as e:
            print(f"❌ Order error: {e}")
    
    async def update_inventory(self, store_id: str, 
                             product_id: str, quantity: float):
        """Reduce inventory"""
        # Get current stock
        response = self.supabase.table("inventory")\
            .select("quantity")\
            .eq("store_id", store_id)\
            .eq("product_id", product_id)\
            .execute()
        
        if response.data:
            current = float(response.data[0]["quantity"])
            new = current - quantity
            
            # Update
            self.supabase.table("inventory")\
                .update({"quantity": new})\
                .eq("store_id", store_id)\
                .eq("product_id", product_id)\
                .execute()
            
            print(f"📦 Stock updated: {current} → {new}")
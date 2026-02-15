from anthropic import AsyncAnthropic
from events.event_bus import event_bus, Event
from supabase import create_client
from datetime import datetime
import os
import sys

class SummaryAgent:
    """Generates daily summaries with AI"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.anthropic = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        event_bus.subscribe("generate_daily_summary", self.handle_summary)
        print("✅ Summary Agent ready (with Anthropic API)")
    
    async def handle_summary(self, event: Event):
        """Generate AI summary"""
        print(f"📊 Generating summary...", flush=True)
        
        try:
            # Get today's data
            print(f"🔍 Fetching daily data...", flush=True)
            data = await self.get_daily_data(event.store_id)
            print(f"📦 Data fetched: {data}", flush=True)
            
            # Create prompt for Claude
            prompt = f"""You are a business analyst for a kirana store.

Today's Performance:
- Revenue: ₹{data['revenue']}
- Orders: {data['orders']}
- Top Products: {', '.join(data['top_products'])}
- Low Stock: {', '.join(data['low_stock'])}

Generate a brief summary in Hinglish (Hindi-English mix) in 4-5 sentences that:
1. Highlights key wins
2. Points out concerns
3. Gives 2-3 actionable tips

Keep it friendly and practical. Maximum 150 words."""

            print(f"🤖 Calling Claude API...", flush=True)
            # Use Anthropic API directly
            message = await self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = message.content[0].text
            print(f"✅ Summary generated!", flush=True)
            
            # Print to console with clear formatting
            print(f"\n{'='*60}", flush=True)
            print(f"DAILY SUMMARY FOR STORE: {event.store_id}", flush=True)
            print(f"{'='*60}", flush=True)
            print(summary, flush=True)
            print(f"{'='*60}\n", flush=True)
            
            # Save to database
            print(f"💾 Saving to database...", flush=True)
            await self.save_summary(event.store_id, summary, data)
            print(f"✅ All done!", flush=True)
            
        except Exception as e:
            print(f"❌ Summary error: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    async def save_summary(self, store_id: str, summary: str, data: dict):
        """Save summary to database"""
        try:
            print(f"📝 Preparing data for insertion...", flush=True)
            insert_data = {
                "store_id": store_id,
                "summary": summary,
                "revenue": float(data["revenue"]),
                "order_count": data["orders"],
                "top_products": data["top_products"],
                "low_stock_items": data["low_stock"],
                "created_at": datetime.now().isoformat()
            }
            print(f"📊 Insert data: {insert_data}", flush=True)
            
            result = self.supabase.table("daily_summaries").insert(insert_data).execute()
            
            print(f"💾 Summary saved to database!", flush=True)
            print(f"📄 Result: {result.data}", flush=True)
            
        except Exception as e:
            print(f"⚠️ Could not save summary to DB: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    async def get_daily_data(self, store_id: str):
        """Collect today's stats"""
        today = datetime.now().date()
        
        try:
            # Get orders
            orders = self.supabase.table("orders")\
                .select("total_amount")\
                .eq("store_id", store_id)\
                .gte("created_at", today.isoformat())\
                .execute()
            
            revenue = sum(float(o["total_amount"]) for o in orders.data)
            count = len(orders.data)
            
            # Get low stock
            inventory = self.supabase.table("inventory")\
                .select("*, products(name)")\
                .eq("store_id", store_id)\
                .execute()
            
            low_stock = [
                item["products"]["name"]
                for item in inventory.data
                if item["quantity"] < item["reorder_threshold"]
            ]
            
            return {
                "revenue": revenue,
                "orders": count,
                "top_products": ["Atta", "Rice", "Sugar"],
                "low_stock": low_stock if low_stock else ["None"]
            }
        except Exception as e:
            print(f"❌ Error getting daily data: {e}", flush=True)
            raise
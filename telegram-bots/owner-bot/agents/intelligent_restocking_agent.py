"""
Intelligent Restocking Agent - Uses Claude AI for smart inventory decisions
Analyzes patterns, predicts demand, and provides actionable insights
"""
import os
from anthropic import Anthropic
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib.parse
import json

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
bot = Bot(token=os.getenv("OWNER_BOT_TOKEN"))

async def analyze_inventory_with_ai(store_id: str):
    """Use Claude to analyze inventory and provide intelligent recommendations"""
    try:
        # Get store details
        store = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        if not store.data:
            return False
        
        chat_id = store.data.get("telegram_chat_id")
        if not chat_id:
            return False
        
        # Get inventory data
        inventory = supabase.table("inventory")\
            .select("*, products(name, supplier_name, supplier_whatsapp, cost_price, unit)")\
            .eq("store_id", store_id)\
            .execute()
        
        # Get recent orders (last 30 days)
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        orders = supabase.table("order_items")\
            .select("*, orders!inner(store_id, created_at), products(name)")\
            .eq("orders.store_id", store_id)\
            .gte("orders.created_at", month_ago)\
            .execute()
        
        # Prepare data for Claude
        inventory_summary = []
        for item in inventory.data:
            product = item['products']
            quantity = float(item['quantity'])
            threshold = float(item.get('reorder_threshold', 10))
            
            # Calculate sales from orders
            product_sales = [
                float(o['quantity']) 
                for o in orders.data 
                if o['product_id'] == item['product_id']
            ]
            total_sold = sum(product_sales)
            avg_daily_sales = total_sold / 30 if total_sold > 0 else 0
            
            inventory_summary.append({
                "product": product['name'],
                "current_stock": quantity,
                "reorder_threshold": threshold,
                "total_sold_30days": total_sold,
                "avg_daily_sales": round(avg_daily_sales, 2),
                "supplier": product.get('supplier_name'),
                "cost_price": float(product.get('cost_price', 0)),
                "unit": product.get('unit', 'unit')
            })
        
        # Ask Claude for analysis
        prompt = f"""You are an intelligent inventory management assistant for a retail store.

Store: {store.data['name']}

Current Inventory Status:
{json.dumps(inventory_summary, indent=2)}

Analyze this inventory data and provide:
1. Which products need immediate restocking (critical)
2. Which products should be restocked soon (warning)
3. Sales velocity insights (fast/slow moving items)
4. Cost-effective restocking recommendations
5. Any patterns or trends you notice

Format your response as a clear, actionable Telegram message with emojis.
Keep it concise but insightful. Focus on actionable recommendations."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        ai_analysis = message.content[0].text
        
        # Send AI analysis to owner
        await bot.send_message(
            chat_id=chat_id,
            text=f"🤖 *AI Inventory Analysis*\n\n{ai_analysis}",
            parse_mode='Markdown'
        )
        
        # Send individual alerts for critical items
        critical_items = [
            item for item in inventory_summary 
            if item['current_stock'] <= item['reorder_threshold']
        ]
        
        for item in critical_items:
            product_data = next(
                (inv for inv in inventory.data if inv['products']['name'] == item['product']),
                None
            )
            
            if product_data and product_data['products'].get('supplier_whatsapp'):
                whatsapp = product_data['products']['supplier_whatsapp']
                reorder_qty = item['reorder_threshold'] * 2
                
                whatsapp_msg = f"Hi, urgent reorder needed for {item['product']}. Please send {reorder_qty:.0f} {item['unit']}."
                whatsapp_url = f"https://wa.me/{whatsapp}?text={urllib.parse.quote(whatsapp_msg)}"
                
                keyboard = [[InlineKeyboardButton("📱 Contact Supplier", url=whatsapp_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ *Critical: {item['product']}*\n"
                         f"Stock: {item['current_stock']:.0f} {item['unit']}\n"
                         f"Suggested reorder: {reorder_qty:.0f} {item['unit']}",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        
        print(f"✅ AI analysis sent to store {store_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error in AI analysis: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python intelligent_restocking_agent.py <store_id>")
        sys.exit(1)
    
    store_id = sys.argv[1]
    asyncio.run(analyze_inventory_with_ai(store_id))

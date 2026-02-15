"""
AI-Powered Daily Report Agent - Uses Claude for intelligent business insights
Analyzes daily performance and provides actionable recommendations
"""
import os
from datetime import datetime, date
from anthropic import Anthropic
from telegram import Bot
from supabase import create_client
from dotenv import load_dotenv
import json

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

async def generate_daily_report(store_id: str):
    """Generate AI-powered daily sales report with insights"""
    try:
        # Get store details
        store = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        
        if not store.data:
            return False
        
        chat_id = store.data.get("telegram_chat_id")
        if not chat_id:
            return False
        
        today = date.today().isoformat()
        
        # Get today's orders with details
        orders = supabase.table("orders")\
            .select("*, order_items(*, products(name, category_id, categories(name)))")\
            .eq("store_id", store_id)\
            .gte("created_at", today)\
            .execute()
        
        if not orders.data:
            simple_message = f"""
📊 *Daily Report - {datetime.now().strftime('%d %B %Y')}*

No orders today. 

💡 *AI Suggestion:* Consider promoting your products or reaching out to regular customers!
"""
            await bot.send_message(chat_id=chat_id, text=simple_message, parse_mode='Markdown')
            return True
        
        # Calculate stats
        total_orders = len(orders.data)
        total_revenue = sum(float(o['total_amount']) for o in orders.data)
        total_profit = sum(float(o.get('profit_amount', 0)) for o in orders.data)
        
        # Category-wise breakdown
        category_sales = {}
        product_sales = {}
        
        for order in orders.data:
            for item in order.get('order_items', []):
                # Category
                cat_name = item['products']['categories']['name'] if item['products'].get('categories') else 'Uncategorized'
                if cat_name not in category_sales:
                    category_sales[cat_name] = {'quantity': 0, 'revenue': 0}
                category_sales[cat_name]['quantity'] += float(item['quantity'])
                category_sales[cat_name]['revenue'] += float(item['unit_price']) * float(item['quantity'])
                
                # Product
                prod_name = item['products']['name']
                if prod_name not in product_sales:
                    product_sales[prod_name] = 0
                product_sales[prod_name] += float(item['quantity'])
        
        # Prepare data for Claude
        report_data = {
            "store_name": store.data['name'],
            "date": datetime.now().strftime('%d %B %Y'),
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "profit_margin": round((total_profit / total_revenue * 100) if total_revenue > 0 else 0, 1),
            "category_sales": category_sales,
            "top_products": dict(sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5])
        }
        
        # Ask Claude for insights
        prompt = f"""You are a business analyst for a retail store. Analyze today's performance and provide insights.

Daily Performance Data:
{json.dumps(report_data, indent=2)}

Provide:
1. Performance summary (good/average/needs improvement)
2. Key highlights and achievements
3. Top performing categories and products
4. Profit margin analysis
5. Actionable recommendations for tomorrow
6. Any concerning trends

Format as a clear, motivating Telegram message with emojis. Keep it concise but insightful."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        ai_insights = message.content[0].text
        
        # Send AI-powered report
        final_report = f"""📊 *Daily Report - {datetime.now().strftime('%d %B %Y')}*

📈 *Quick Stats:*
• Orders: {total_orders}
• Revenue: ₹{total_revenue:,.2f}
• Profit: ₹{total_profit:,.2f}
• Margin: {report_data['profit_margin']}%

{ai_insights}
"""
        
        await bot.send_message(
            chat_id=chat_id,
            text=final_report,
            parse_mode='Markdown'
        )
        
        print(f"✅ AI daily report sent to store {store_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error generating AI daily report: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python daily_report_agent.py <store_id>")
        sys.exit(1)
    
    store_id = sys.argv[1]
    asyncio.run(generate_daily_report(store_id))

"""
Intelligent Credit Analyzer - Uses Claude AI for credit risk assessment
Provides personalized collection strategies and payment predictions
"""
import os
from anthropic import Anthropic
from telegram import Bot
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

async def analyze_credit_with_ai(store_id: str):
    """Use Claude to analyze credit patterns and provide collection strategies"""
    try:
        # Get store details
        store = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        if not store.data:
            return False
        
        chat_id = store.data.get("telegram_chat_id")
        if not chat_id:
            return False
        
        # Get credit orders
        orders = supabase.table("orders")\
            .select("*, customers(name, phone)")\
            .eq("store_id", store_id)\
            .in_("status", ["pending", "credit"])\
            .execute()
        
        if not orders.data or len(orders.data) == 0:
            print(f"✅ No credit orders for store {store_id}")
            return True
        
        # Prepare credit data
        credit_accounts = []
        for order in orders.data:
            customer = order.get('customers', {})
            days_pending = (datetime.now() - datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))).days
            
            credit_accounts.append({
                "customer_name": customer.get('name', 'Unknown'),
                "customer_phone": customer.get('phone', 'N/A'),
                "amount_due": float(order['total_amount']),
                "days_pending": days_pending,
                "order_date": order['created_at'][:10]
            })
        
        total_credit = sum(acc['amount_due'] for acc in credit_accounts)
        
        # Ask Claude for analysis
        prompt = f"""You are a financial advisor helping a small retail store manage credit accounts.

Store: {store.data['name']}
Total Outstanding: ₹{total_credit:,.2f}

Credit Accounts:
{json.dumps(credit_accounts, indent=2)}

Provide:
1. Risk assessment for each account (High/Medium/Low risk)
2. Personalized collection strategies for each customer
3. Priority order for follow-ups
4. Suggested communication approach (friendly reminder vs firm notice)
5. Payment plan recommendations if needed

Format as a clear, actionable Telegram message with emojis.
Be professional but empathetic - these are small business relationships."""

        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        ai_analysis = message.content[0].text
        
        # Send AI analysis
        await bot.send_message(
            chat_id=chat_id,
            text=f"💳 *AI Credit Analysis*\n\n{ai_analysis}",
            parse_mode='Markdown'
        )
        
        print(f"✅ AI credit analysis sent to store {store_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error in AI credit analysis: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python intelligent_credit_agent.py <store_id>")
        sys.exit(1)
    
    store_id = sys.argv[1]
    asyncio.run(analyze_credit_with_ai(store_id))

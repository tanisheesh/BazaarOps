import asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Initialize
BOT_TOKEN = os.getenv("OWNER_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Auto-link if user is registered"""
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    
    try:
        # Check if user already linked
        existing = supabase.table("stores")\
            .select("id, name")\
            .eq("telegram_chat_id", str(chat_id))\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            store = existing.data[0]
            await update.message.reply_text(
                f"✅ *Already Linked!*\n\n"
                f"Store: {store['name']}\n\n"
                f"You're receiving automated updates! 🤖",
                parse_mode='Markdown'
            )
            return
        
        # Try to auto-link by username
        if username:
            store_response = supabase.table("stores")\
                .select("id, name, phone")\
                .eq("telegram_username", username)\
                .execute()
            
            if store_response.data and len(store_response.data) > 0:
                store = store_response.data[0]
                
                # Auto-link!
                supabase.table("stores")\
                    .update({"telegram_chat_id": str(chat_id)})\
                    .eq("id", store["id"])\
                    .execute()
                
                # Send welcome message
                await update.message.reply_text(
                    f"🎉 *Welcome to BazaarOps Admin!* 🎉\n\n"
                    f"Hello {store['name']}! 👋\n\n"
                    f"✅ *Your store is now linked!*\n\n"
                    f"🔔 *You'll now receive:*\n"
                    f"• Real-time low stock alerts\n"
                    f"• Daily sales reports at 9 PM\n"
                    f"• Credit analysis\n"
                    f"• Order notifications\n\n"
                    f"📊 Use /status to check your stats anytime!\n\n"
                    f"Let's grow your business together! 🚀",
                    parse_mode='Markdown'
                )
                
                print(f"✅ Auto-linked: {store['name']} (@{username})")
                return
        
        # Not found - ask for manual registration
        await update.message.reply_text(
            "🛒 *Welcome to BazaarOps Admin!*\n\n"
            "To link your store, please use:\n"
            "/register <phone_number>\n\n"
            "Example: /register 9876543210",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Start command error: {e}")
        await update.message.reply_text(
            "❌ Something went wrong. Please try again or contact support."
        )

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register owner's telegram chat ID with their store"""
    chat_id = update.effective_chat.id
    
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Please provide your phone number\n\n"
            "Format: /register 9876543210"
        )
        return
    
    phone = context.args[0].strip()
    
    try:
        # Find store by phone number
        response = supabase.table("stores")\
            .select("id, name, owner_id")\
            .eq("phone", phone)\
            .execute()
        
        if not response.data or len(response.data) == 0:
            await update.message.reply_text(
                "❌ No store found with this phone number.\n\n"
                "Please contact support or check your phone number."
            )
            return
        
        store = response.data[0]
        
        # Update telegram_chat_id
        supabase.table("stores")\
            .update({"telegram_chat_id": str(chat_id)})\
            .eq("id", store["id"])\
            .execute()
        
        await update.message.reply_text(
            f"✅ *Registration Successful!*\n\n"
            f"Store: {store['name']}\n"
            f"Phone: {phone}\n\n"
            f"You will now receive:\n"
            f"• Daily business summary at 9 AM\n"
            f"• Low stock alerts at 10 AM & 4 PM\n"
            f"• Evening report at 8 PM\n"
            f"• New order notifications\n\n"
            f"Stay updated! 📊",
            parse_mode='Markdown'
        )
        
        print(f"✅ Registered: {store['name']} (Chat ID: {chat_id})")
        
    except Exception as e:
        print(f"❌ Registration error: {e}")
        await update.message.reply_text(
            "❌ Registration failed. Please try again or contact support."
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check registration status"""
    chat_id = update.effective_chat.id
    
    try:
        response = supabase.table("stores")\
            .select("id, name, phone")\
            .eq("telegram_chat_id", str(chat_id))\
            .execute()
        
        if not response.data or len(response.data) == 0:
            await update.message.reply_text(
                "❌ You are not registered yet.\n\n"
                "Use /register <phone_number> to register."
            )
            return
        
        store = response.data[0]
        
        # Get today's stats
        today = datetime.now().date()
        orders_response = supabase.table("orders")\
            .select("total_amount, status")\
            .eq("store_id", store["id"])\
            .gte("created_at", today.isoformat())\
            .execute()
        
        total_orders = len(orders_response.data)
        total_revenue = sum(float(o["total_amount"]) for o in orders_response.data)
        
        await update.message.reply_text(
            f"✅ *Registration Status*\n\n"
            f"Store: {store['name']}\n"
            f"Phone: {store['phone']}\n\n"
            f"📊 *Today's Stats:*\n"
            f"Orders: {total_orders}\n"
            f"Revenue: ₹{total_revenue:.2f}\n\n"
            f"Bot is active! 🤖",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Status check error: {e}")
        await update.message.reply_text("❌ Error checking status.")

async def send_message_to_owner(store_id: str, message: str):
    """Send message to specific store owner"""
    try:
        # Get store's telegram chat ID
        response = supabase.table("stores")\
            .select("telegram_chat_id, name")\
            .eq("id", store_id)\
            .execute()
        
        if not response.data or len(response.data) == 0:
            print(f"❌ Store {store_id} not found")
            return False
        
        store = response.data[0]
        chat_id = store.get("telegram_chat_id")
        
        if not chat_id:
            print(f"⚠️ Store {store['name']} has no telegram_chat_id")
            return False
        
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        
        print(f"✅ Message sent to {store['name']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def main():
    """Main function - Bot with Claude AI Agents"""
    print("🤖 BazaarOps Admin Bot")
    print("=" * 50)
    print("🧠 Powered by Claude AI Agents")
    print("=" * 50)
    
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("register", register_command))
        application.add_handler(CommandHandler("status", status_command))
        
        print("\n🚀 Bot is running...")
        print("📱 Commands:")
        print("  • /start - Auto-link your store")
        print("  • /register <phone> - Manual registration")
        print("  • /status - Check your stats")
        print("\n🧠 AI Agents handle:")
        print("  • Intelligent inventory analysis")
        print("  • Credit risk assessment")
        print("  • Daily business insights")
        print("\nPress Ctrl+C to stop\n")
        
        # Run bot - simple polling
        application.run_polling()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

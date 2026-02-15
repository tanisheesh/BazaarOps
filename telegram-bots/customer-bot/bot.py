from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv
from pathlib import Path
import httpx
import os

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Configuration
CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8002").strip()
BOT_TOKEN = os.getenv("CUSTOMER_BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN in .env")

# Store user sessions (in-memory for now)
user_sessions = {}

# Start command with deep linking
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts bot - supports deep linking"""
    user_id = update.effective_user.id
    
    # Check if store_id provided via deep link
    # Format: /start STORE_ID
    if context.args and len(context.args) > 0:
        store_id = context.args[0]
        user_sessions[user_id] = {"store_id": store_id}
        
        # Save to database
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{CUSTOMER_SERVICE_URL}/api/customer/register",
                    json={
                        "telegram_user_id": user_id,
                        "telegram_username": update.effective_user.username,
                        "store_id": store_id
                    }
                )
        except Exception as e:
            print(f"Error registering customer: {e}")
        
        keyboard = [
            [KeyboardButton("📦 View Products")],
            [KeyboardButton("🛍️ Place Order")],
            [KeyboardButton("📋 My Orders")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🛒 *Welcome to BazaarOps!*\n\n"
            "I'm your personal shopping assistant.\n\n"
            "✅ You're connected to the store!\n\n"
            "What would you like to do?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # No store_id provided
        await update.message.reply_text(
            "👋 Welcome to BazaarOps!\n\n"
            "⚠️ Please use the link provided by your store to start shopping.\n\n"
            "Store owners can share:\n"
            f"`https://t.me/{context.bot.username}?start=STORE_ID`",
            parse_mode='Markdown'
        )

# View products
async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and show products"""
    user_id = update.effective_user.id
    
    # Get store_id from session
    if user_id not in user_sessions:
        await update.message.reply_text(
            "⚠️ Please start the bot using the link from your store."
        )
        return
    
    store_id = user_sessions[user_id]["store_id"]
    await update.message.reply_text("📦 Fetching products...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{store_id}",
                timeout=10.0
            )
            data = response.json()
        
        if not data.get("success"):
            await update.message.reply_text("❌ Could not fetch products")
            return
        
        products = data.get("products", [])
        
        if not products:
            await update.message.reply_text("No products available.")
            return
        
        # Format products nicely
        message = "📦 *Available Products:*\n\n"
        for i, product in enumerate(products, 1):
            message += f"{i}. *{product['name']}*\n"
            message += f"   ₹{product['price']}/{product['unit']}\n"
            message += f"   Available: {product['available']} {product['unit']}\n"
            if product.get('description'):
                message += f"   _{product['description']}_\n"
            message += "\n"
        
        message += "💡 To order, type:\n`order <product> <quantity>`\n\n"
        message += "Example: `order Atta 2`"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error fetching products. Try again!")

# Process order
async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process order from text"""
    user_id = update.effective_user.id
    
    # Get store_id from session
    if user_id not in user_sessions:
        await update.message.reply_text(
            "⚠️ Please start the bot using the link from your store."
        )
        return
    
    store_id = user_sessions[user_id]["store_id"]
    
    try:
        # Parse "order Atta 2"
        parts = update.message.text.split()
        
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Format: `order <product> <quantity>`\n"
                "Example: `order Atta 2`",
                parse_mode='Markdown'
            )
            return
        
        # Extract product name and quantity
        product_name = " ".join(parts[1:-1])
        quantity = float(parts[-1])
        
        # Use Telegram user ID as phone
        customer_phone = str(update.effective_user.id)
        
        await update.message.reply_text(
            f"🔄 Processing order for {quantity} {product_name}..."
        )
        
        # Get products first
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{store_id}"
            )
            products_data = products_response.json()
        
        # Find matching product
        matching_product = None
        for product in products_data.get("products", []):
            if product_name.lower() in product["name"].lower():
                matching_product = product
                break
        
        if not matching_product:
            await update.message.reply_text(
                f"❌ '{product_name}' not found.\n"
                "Type 'view products' to see what's available."
            )
            return
        
        # Check availability
        if quantity > matching_product["available"]:
            await update.message.reply_text(
                f"❌ Only {matching_product['available']} "
                f"{matching_product['unit']} available."
            )
            return
        
        # Place order
        order_data = {
            "customer_phone": customer_phone,
            "items": [
                {
                    "product_id": matching_product["product_id"],
                    "product_name": matching_product["name"],
                    "quantity": quantity,
                    "unit_price": matching_product["price"]
                }
            ],
            "is_credit": False
        }
        
        async with httpx.AsyncClient() as client:
            order_response = await client.post(
                f"{CUSTOMER_SERVICE_URL}/api/customer/order/{store_id}",
                json=order_data,
                timeout=10.0
            )
            order_result = order_response.json()
        
        if order_result.get("success"):
            total = quantity * matching_product["price"]
            await update.message.reply_text(
                f"✅ *Order Placed!*\n\n"
                f"Product: {matching_product['name']}\n"
                f"Quantity: {quantity} {matching_product['unit']}\n"
                f"Price: ₹{matching_product['price']}/{matching_product['unit']}\n"
                f"*Total: ₹{total}*\n\n"
                f"Order ID: `{order_result['order_id'][:8]}...`\n\n"
                f"Store will confirm soon!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Could not place order. Try again!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity. Use a number.")
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error processing order. Try again!")

# Handle all text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route messages to correct handler"""
    text = update.message.text.lower()
    
    if "view products" in text or "📦" in text:
        await view_products(update, context)
    
    elif "place order" in text or "🛍️" in text:
        await update.message.reply_text(
            "📝 To place order:\n`order <product> <quantity>`\n\n"
            "Example: `order Atta 2`",
            parse_mode='Markdown'
        )
    
    elif text.startswith("order "):
        await process_order(update, context)
    
    else:
        await update.message.reply_text(
            "Try:\n"
            "• 📦 View Products\n"
            "• Type: order <product> <quantity>"
        )

# Main function
def main():
    """Start the bot"""
    print("🤖 Starting Customer Bot...")
    print("🔗 Deep linking enabled - customers can start with store-specific links")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    print("✅ Bot is running!")
    print("📱 Share link format: https://t.me/BazaarOpsCustomerHelpBot?start=STORE_ID")
    print("Press Ctrl+C to stop")
    
    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()
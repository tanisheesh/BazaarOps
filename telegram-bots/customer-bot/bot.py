from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from dotenv import load_dotenv
from pathlib import Path
import httpx
import os
import re

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Configuration
CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8002").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("CUSTOMER_BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise SystemExit("Missing CUSTOMER_BOT_TOKEN in .env")

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Store user sessions
user_sessions = {}

# Conversation states
ASKING_NAME, ASKING_PHONE, ASKING_ADDRESS = range(3)
EDIT_NAME, EDIT_PHONE, EDIT_ADDRESS = range(3, 6)

# Get store name
def get_store_name(store_id):
    try:
        store = supabase.table("stores").select("name").eq("id", store_id).single().execute()
        return store.data.get("name", "Our Store") if store.data else "Our Store"
    except:
        return "Our Store"

# Check if customer exists
async def get_customer_data(telegram_user_id, store_id):
    try:
        customer = supabase.table("customers").select("*").eq("telegram_chat_id", str(telegram_user_id)).eq("store_id", store_id).single().execute()
        return customer.data if customer.data else None
    except:
        return None

# Main menu keyboard
def get_main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📦 View Products")],
        [KeyboardButton("🛍️ Place Order"), KeyboardButton("📋 My Orders")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("🏪 My Stores")]
    ], resize_keyboard=True)

# Start command with deep linking
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts bot - supports deep linking"""
    user_id = update.effective_user.id
    
    # Check if store_id provided via deep link
    if context.args and len(context.args) > 0:
        store_id = context.args[0]
        store_name = get_store_name(store_id)
        
        # Save store_id in session
        if user_id not in user_sessions:
            user_sessions[user_id] = {}
        user_sessions[user_id]["store_id"] = store_id
        
        # Check if customer already registered
        customer = await get_customer_data(user_id, store_id)
        
        if customer:
            # Already registered
            await update.message.reply_text(
                f"� *Welcome back to {store_name}!*\n\n"
                f"Hi {customer['name']}! 👋\n\n"
                f"Ready to shop?",
                reply_markup=get_main_menu(),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        else:
            # New customer - start onboarding
            await update.message.reply_text(
                f"🛒 *Welcome to {store_name}!*\n\n"
                f"I'm your personal shopping assistant.\n\n"
                f"Let's get you set up! 📝\n\n"
                f"What's your name?",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='Markdown'
            )
            return ASKING_NAME
    else:
        await update.message.reply_text(
            "👋 Welcome to BazaarOps!\n\n"
            "⚠️ Please use the link provided by your store to start shopping.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

# Onboarding: Get name
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text("Please enter a valid name (at least 2 characters):")
        return ASKING_NAME
    
    user_sessions[user_id]["name"] = name
    
    await update.message.reply_text(
        f"Great, {name}! 👍\n\n"
        f"Now, please enter your phone number (10 digits only):\n\n"
        f"Example: 9876543210"
    )
    return ASKING_PHONE

# Onboarding: Get phone
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    
    if not re.match(r'^\d{10}$', phone):
        await update.message.reply_text(
            "❌ Please enter exactly 10 digits (without +91):\n\n"
            "Example: 9876543210"
        )
        return ASKING_PHONE
    
    user_sessions[user_id]["phone"] = f"+91{phone}"
    
    await update.message.reply_text(
        "📍 Finally, what's your delivery address?\n\n"
        "Example: 123, Main Street, City - 123456"
    )
    return ASKING_ADDRESS

# Onboarding: Get address and complete registration
async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address = update.message.text.strip()
    
    if len(address) < 10:
        await update.message.reply_text("Please enter a complete address (at least 10 characters):")
        return ASKING_ADDRESS
    
    user_sessions[user_id]["address"] = address
    
    try:
        store_id = user_sessions[user_id]["store_id"]
        store_name = get_store_name(store_id)
        
        customer_data = {
            "store_id": store_id,
            "name": user_sessions[user_id]["name"],
            "phone": user_sessions[user_id]["phone"],
            "address": address,
            "telegram_chat_id": str(user_id),
            "telegram_username": update.effective_user.username
        }
        
        supabase.table("customers").insert(customer_data).execute()
        
        await update.message.reply_text(
            f"✅ *Registration Complete!*\n\n"
            f"Welcome to {store_name}! 🎉\n\n"
            f"You can now browse products and place orders.\n\n"
            f"Use '👤 My Profile' to update your details anytime.",
            reply_markup=get_main_menu(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        print(f"❌ Error saving customer: {e}")
        await update.message.reply_text(
            "❌ Error completing registration. Please try /start again."
        )
    
    return ConversationHandler.END

# View profile
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await update.message.reply_text("⚠️ Please start the bot using your store link first.")
        return
    
    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    
    if not customer:
        await update.message.reply_text("❌ Profile not found. Please register first.")
        return
    
    keyboard = [
        [KeyboardButton("✏️ Edit Name"), KeyboardButton("✏️ Edit Phone")],
        [KeyboardButton("✏️ Edit Address")],
        [KeyboardButton("🔙 Back to Menu")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"👤 *Your Profile*\n\n"
        f"Name: {customer['name']}\n"
        f"Phone: {customer['phone']}\n"
        f"Address: {customer['address']}\n\n"
        f"Tap a button to edit:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Edit handlers
async def start_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ Enter your new name:",
        reply_markup=ReplyKeyboardRemove()
    )
    return EDIT_NAME

async def save_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_name = update.message.text.strip()
    
    if len(new_name) < 2:
        await update.message.reply_text("Please enter a valid name:")
        return EDIT_NAME
    
    try:
        store_id = user_sessions[user_id]["store_id"]
        supabase.table("customers")\
            .update({"name": new_name})\
            .eq("telegram_chat_id", str(user_id))\
            .eq("store_id", store_id)\
            .execute()
        
        await update.message.reply_text(
            f"✅ Name updated to: {new_name}",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error updating name.")
    
    return ConversationHandler.END

async def start_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ Enter your new phone number (10 digits):\n\nExample: 9876543210",
        reply_markup=ReplyKeyboardRemove()
    )
    return EDIT_PHONE

async def save_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    
    if not re.match(r'^\d{10}$', phone):
        await update.message.reply_text("❌ Please enter exactly 10 digits:")
        return EDIT_PHONE
    
    try:
        store_id = user_sessions[user_id]["store_id"]
        supabase.table("customers")\
            .update({"phone": f"+91{phone}"})\
            .eq("telegram_chat_id", str(user_id))\
            .eq("store_id", store_id)\
            .execute()
        
        await update.message.reply_text(
            f"✅ Phone updated to: +91{phone}",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error updating phone.")
    
    return ConversationHandler.END

async def start_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ Enter your new address:",
        reply_markup=ReplyKeyboardRemove()
    )
    return EDIT_ADDRESS

async def save_edit_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address = update.message.text.strip()
    
    if len(address) < 10:
        await update.message.reply_text("Please enter a complete address:")
        return EDIT_ADDRESS
    
    try:
        store_id = user_sessions[user_id]["store_id"]
        supabase.table("customers")\
            .update({"address": address})\
            .eq("telegram_chat_id", str(user_id))\
            .eq("store_id", store_id)\
            .execute()
        
        await update.message.reply_text(
            f"✅ Address updated!",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error updating address.")
    
    return ConversationHandler.END

# View visited stores
async def view_stores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        customers = supabase.table("customers")\
            .select("store_id, stores(name)")\
            .eq("telegram_chat_id", str(user_id))\
            .execute()
        
        if not customers.data:
            await update.message.reply_text("You haven't visited any stores yet.")
            return
        
        message = "🏪 *Your Stores:*\n\n"
        for i, customer in enumerate(customers.data, 1):
            store_name = customer['stores']['name'] if customer.get('stores') else "Unknown Store"
            message += f"{i}. {store_name}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error fetching stores.")

# View products
async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await update.message.reply_text("⚠️ Please start the bot using your store link first.")
        return
    
    store_id = user_sessions[user_id]["store_id"]
    store_name = get_store_name(store_id)
    
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
        
        message = f"📦 *{store_name} - Products:*\n\n"
        for i, product in enumerate(products, 1):
            message += f"{i}. *{product['name']}*\n"
            message += f"   ₹{product['price']}/{product['unit']}\n"
            message += f"   Available: {product['available']} {product['unit']}\n\n"
        
        message += "💡 To order: `order <product> <quantity>`\n"
        message += "Example: `order Rice 2`"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error fetching products.")

# Place order
async def place_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await update.message.reply_text("⚠️ Please start the bot using your store link first.")
        return
    
    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    
    if not customer:
        await update.message.reply_text("❌ Please complete registration first.")
        return
    
    try:
        parts = update.message.text.split()
        
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Format: `order <product> <quantity>`\n"
                "Example: `order Rice 2`",
                parse_mode='Markdown'
            )
            return
        
        product_name = " ".join(parts[1:-1])
        quantity = float(parts[-1])
        
        await update.message.reply_text(f"🔄 Processing order for {quantity} {product_name}...")
        
        # Get products
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
            await update.message.reply_text(f"❌ '{product_name}' not found.")
            return
        
        if quantity > matching_product["available"]:
            await update.message.reply_text(
                f"❌ Only {matching_product['available']} {matching_product['unit']} available."
            )
            return
        
        # Place order
        order_data = {
            "customer_phone": customer["phone"],
            "items": [{
                "product_id": matching_product["product_id"],
                "product_name": matching_product["name"],
                "quantity": quantity,
                "unit_price": matching_product["price"]
            }],
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
                f"✅ *Order Confirmed!*\n\n"
                f"Product: {matching_product['name']}\n"
                f"Quantity: {quantity} {matching_product['unit']}\n"
                f"Price: ₹{matching_product['price']}/{matching_product['unit']}\n"
                f"*Total: ₹{total}*\n\n"
                f"Order ID: `{order_result['order_id'][:8]}...`\n\n"
                f"We'll update you when it's delivered! 📦",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Could not place order.")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity.")
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error processing order.")

# View orders
async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await update.message.reply_text("⚠️ Please start the bot using your store link first.")
        return
    
    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    
    if not customer:
        await update.message.reply_text("❌ Profile not found.")
        return
    
    try:
        orders = supabase.table("orders")\
            .select("id, total_amount, status, created_at")\
            .eq("customer_id", customer["id"])\
            .order("created_at", desc=True)\
            .limit(10)\
            .execute()
        
        if not orders.data:
            await update.message.reply_text("📋 No orders yet.")
            return
        
        message = "📋 *Your Recent Orders:*\n\n"
        for order in orders.data:
            status_emoji = "✅" if order["status"] == "completed" else "🔄" if order["status"] == "confirmed" else "⏳"
            message += f"{status_emoji} Order: `{order['id'][:8]}...`\n"
            message += f"   Amount: ₹{order['total_amount']}\n"
            message += f"   Status: {order['status'].title()}\n\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error fetching orders.")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if "📦" in text or "view products" in text.lower():
        await view_products(update, context)
    elif "👤" in text or "my profile" in text.lower():
        await view_profile(update, context)
    elif "🏪" in text or "my stores" in text.lower():
        await view_stores(update, context)
    elif "📋" in text or "my orders" in text.lower():
        await view_orders(update, context)
    elif "🛍️" in text or "place order" in text.lower():
        await update.message.reply_text(
            "📝 To place order:\n`order <product> <quantity>`\n\n"
            "Example: `order Rice 2`",
            parse_mode='Markdown'
        )
    elif text.lower().startswith("order "):
        await place_order(update, context)
    elif "🔙" in text or "back" in text.lower():
        await update.message.reply_text("Main menu:", reply_markup=get_main_menu())
    else:
        await update.message.reply_text(
            "Try:\n"
            "• 📦 View Products\n"
            "• 🛍️ Place Order (type: order <product> <quantity>)\n"
            "• 📋 My Orders\n"
            "• 👤 My Profile\n"
            "• 🏪 My Stores"
        )

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Cancelled. Use the menu buttons.",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END

def main():
    print("🤖 Starting Customer Bot...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Onboarding conversation
    onboarding_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ASKING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Edit name conversation
    edit_name_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Edit Name$"), start_edit_name)],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Edit phone conversation
    edit_phone_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Edit Phone$"), start_edit_phone)],
        states={
            EDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Edit address conversation
    edit_address_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ Edit Address$"), start_edit_address)],
        states={
            EDIT_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_address)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(onboarding_handler)
    application.add_handler(edit_name_handler)
    application.add_handler(edit_phone_handler)
    application.add_handler(edit_address_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot is running!")
    print("📱 Share: https://t.me/BazaarOpsCustomerHelpBot?start=STORE_ID")
    print("Press Ctrl+C to stop")
    
    application.run_polling()

if __name__ == "__main__":
    main()

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from dotenv import load_dotenv
from pathlib import Path
import httpx
import os
import re
import logging

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

logger = logging.getLogger(__name__)

# Configuration
CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8002").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BOT_TOKEN = os.getenv("CUSTOMER_BOT_TOKEN", "").strip()

if not BOT_TOKEN:
    raise SystemExit("Missing CUSTOMER_BOT_TOKEN in .env")

from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# NLP components (5.1 - 5.6)
try:
    from nlp_order_parser import ConversationalOrderParser
    from conversation_manager import (
        ConversationManager,
        STATE_BROWSING, STATE_ORDERING, STATE_AWAITING_CLARIFICATION,
        STATE_CONFIRMING, STATE_CONFIRMED,
    )
    _nlp_parser = ConversationalOrderParser()
    _conv_manager = ConversationManager()
    NLP_ENABLED = bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ENABLE_CONVERSATIONAL_AI", "true").lower() == "true")
    logger.info("✅ NLP components loaded (enabled=%s)", NLP_ENABLED)
except ImportError as e:
    logger.warning("⚠️ NLP components not available: %s — falling back to command mode", e)
    _nlp_parser = None
    _conv_manager = None
    NLP_ENABLED = False

# Store user sessions
user_sessions = {}

# Conversation states
ASKING_NAME, ASKING_PHONE, ASKING_ADDRESS, ASKING_BIRTHDAY = range(4)
EDIT_NAME, EDIT_PHONE, EDIT_ADDRESS = range(4, 7)

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
    
    # 3.2.2 Ask for birthday (optional)
    await update.message.reply_text(
        "🎂 *Almost done!*\n\n"
        "What's your birthday? (optional)\n\n"
        "Format: MM-DD (e.g. 03-15 for March 15)\n\n"
        "Type 'skip' to skip this step.",
        parse_mode='Markdown'
    )
    return ASKING_BIRTHDAY

# Onboarding: Get birthday (optional) and complete registration
async def get_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # 3.2.3 Birthday is optional
    birthday = None
    if text.lower() != "skip":
        if re.match(r'^\d{2}-\d{2}$', text):
            birthday = text
        else:
            await update.message.reply_text(
                "❌ Please use MM-DD format (e.g. 03-15) or type 'skip':"
            )
            return ASKING_BIRTHDAY
    
    user_sessions[user_id]["birthday"] = birthday
    
    try:
        store_id = user_sessions[user_id]["store_id"]
        store_name = get_store_name(store_id)
        
        customer_data = {
            "store_id": store_id,
            "name": user_sessions[user_id]["name"],
            "phone": user_sessions[user_id]["phone"],
            "address": user_sessions[user_id]["address"],
            "telegram_chat_id": str(user_id),
            "telegram_username": update.effective_user.username,
        }
        if birthday:
            customer_data["birthday"] = birthday
        
        supabase.table("customers").insert(customer_data).execute()
        
        birthday_msg = f"\n🎂 Birthday saved: {birthday}" if birthday else ""
        
        await update.message.reply_text(
            f"✅ *Registration Complete!*\n\n"
            f"Welcome to {store_name}! 🎉{birthday_msg}\n\n"
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
        
        # Ask payment method
        
        total = quantity * matching_product["price"]
        keyboard = [
            [
                InlineKeyboardButton("💵 Pay Cash", callback_data=f"pay_cash_{matching_product['product_id']}_{quantity}"),
                InlineKeyboardButton("💳 Credit (Pay Later)", callback_data=f"pay_credit_{matching_product['product_id']}_{quantity}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📦 *Order Summary*\n\n"
            f"Product: {matching_product['name']}\n"
            f"Quantity: {quantity} {matching_product['unit']}\n"
            f"Price: ₹{matching_product['price']}/{matching_product['unit']}\n"
            f"*Total: ₹{total}*\n\n"
            f"Choose payment method:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity.")
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error processing order.")

# Handle payment callback
async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await query.edit_message_text("⚠️ Session expired. Please start again.")
        return
    
    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    
    if not customer:
        await query.edit_message_text("❌ Profile not found.")
        return
    
    try:
        # Parse callback data: pay_cash_<product_id>_<quantity> or pay_credit_<product_id>_<quantity>
        parts = query.data.split("_")
        payment_type = parts[1]  # "cash" or "credit"
        product_id = parts[2]
        quantity = float(parts[3])
        
        is_credit = (payment_type == "credit")
        
        # Credit enforcement (4.3): check limit before allowing credit order
        if is_credit:
            try:
                customer_credit = supabase.table("customers")\
                    .select("credit_limit, credit_suspended, credit_score")\
                    .eq("id", customer["id"])\
                    .single()\
                    .execute()
                credit_data = customer_credit.data or {}
                credit_limit = float(credit_data.get("credit_limit") or 0)
                credit_suspended = bool(credit_data.get("credit_suspended", False))

                # 4.3.3 Block if credit suspended
                if credit_suspended:
                    await query.edit_message_text(
                        "❌ *Credit Unavailable*\n\n"
                        "Your credit account is currently suspended due to an overdue payment.\n"
                        "Please clear your outstanding balance to restore credit.\n\n"
                        "You can still pay with cash.",
                        parse_mode='Markdown'
                    )
                    return

                # Calculate outstanding credit balance
                outstanding_result = supabase.table("orders")\
                    .select("total_amount")\
                    .eq("customer_id", customer["id"])\
                    .eq("payment_status", "unpaid")\
                    .eq("is_credit", True)\
                    .execute()
                outstanding = sum(
                    float(o.get("total_amount", 0))
                    for o in (outstanding_result.data or [])
                )

                # Get product details for total calculation
                async with httpx.AsyncClient() as client:
                    products_response = await client.get(
                        f"{CUSTOMER_SERVICE_URL}/api/customer/products/{store_id}"
                    )
                    products_data = products_response.json()

                order_product = None
                for product in products_data.get("products", []):
                    if product["product_id"] == product_id:
                        order_product = product
                        break

                order_total = float(quantity) * float(order_product["price"]) if order_product else 0.0
                available_credit = credit_limit - outstanding

                # 4.3.2 Show available credit
                if credit_limit == 0:
                    await query.edit_message_text(
                        "❌ *Credit Not Available*\n\n"
                        "Your credit score is too low for credit orders.\n"
                        f"Credit Score: {credit_data.get('credit_score', 50)}/100\n\n"
                        "Please pay with cash or improve your payment history.",
                        parse_mode='Markdown'
                    )
                    return

                # 4.3.3 Block if limit exceeded
                if order_total > available_credit:
                    await query.edit_message_text(
                        f"❌ *Credit Limit Exceeded*\n\n"
                        f"Order Total: ₹{order_total:.0f}\n"
                        f"Available Credit: ₹{available_credit:.0f}\n"
                        f"Credit Limit: ₹{credit_limit:.0f}\n"
                        f"Outstanding Balance: ₹{outstanding:.0f}\n\n"
                        f"Please pay with cash or clear some outstanding balance first.",
                        parse_mode='Markdown'
                    )
                    return
            except Exception as credit_err:
                print(f"⚠️ Credit check error (allowing order): {credit_err}")
        
        # Get product details
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{store_id}"
            )
            products_data = products_response.json()
        
        matching_product = None
        for product in products_data.get("products", []):
            if product["product_id"] == product_id:
                matching_product = product
                break
        
        if not matching_product:
            await query.edit_message_text("❌ Product not found.")
            return
        
        # Place order
        order_data = {
            "customer_phone": customer["phone"],
            "items": [
                {
                    "product_id": product_id,
                    "product_name": matching_product["name"],
                    "quantity": quantity,
                    "unit_price": matching_product["price"]
                }
            ],
            "is_credit": is_credit
        }
        
        async with httpx.AsyncClient() as client:
            order_response = await client.post(
                f"{CUSTOMER_SERVICE_URL}/api/customer/order/{store_id}",
                json=order_data,
                timeout=10.0
            )
            order_result = order_response.json()
        
        if order_result.get("success"):
            payment_status = "💳 Credit (Pay Later)" if is_credit else "💵 Cash on Delivery"
            
            # Delete the payment selection message
            await query.message.delete()
            
            # Send new success message
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ *Order Placed Successfully!*\n\n"
                     f"Order ID: `{order_result['order_id'][:8]}...`\n"
                     f"Product: {matching_product['name']}\n"
                     f"Quantity: {quantity} {matching_product['unit']}\n"
                     f"Total: ₹{order_result['total_amount']}\n"
                     f"Payment: {payment_status}\n\n"
                     f"{'⏳ Your order will be delivered soon!' if not is_credit else '💳 Pay when convenient!'}",
                parse_mode='Markdown',
                reply_markup=get_main_menu()
            )
        else:
            await query.edit_message_text(f"❌ {order_result.get('message', 'Order failed')}")
    
    except Exception as e:
        print(f"❌ Error placing order: {e}")
        await query.edit_message_text("❌ Error placing order. Please try again.")

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

# ---------------------------------------------------------------------------
# NLP message handler (5.6.1 - replaces command-based ordering)
# ---------------------------------------------------------------------------

async def handle_nlp_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    5.6.1 NLP-based order handler. Returns True if handled, False to fall through.
    5.9 Falls back to command-based if NLP fails.
    """
    if not NLP_ENABLED or _nlp_parser is None or _conv_manager is None:
        return False

    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        return False

    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    if not customer:
        return False

    # 5.4.4 Handle follow-up messages — check if awaiting clarification
    conv_state = _conv_manager.get_state(user_id)
    if conv_state == STATE_AWAITING_CLARIFICATION:
        return await _handle_clarification_response(update, context, user_id, store_id, customer, text)

    # 5.4.2 Add user message to history
    conv_context = _conv_manager.add_message(user_id, "user", text)

    # Parse with NLP
    try:
        parsed = await _nlp_parser.parse_order(text, conv_context)
    except Exception as exc:
        logger.error("NLP parse error: %s", exc)
        return False  # 5.9 fallback

    intent = parsed.get("intent", "unknown")
    items = parsed.get("items", [])

    # Only handle place_order intent here; let other intents fall through
    if intent != "place_order" or not items:
        return False

    # Fetch store products for matching
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{store_id}", timeout=10.0
            )
            products_data = resp.json()
        store_products = products_data.get("products", [])
    except Exception as exc:
        logger.error("Failed to fetch products for NLP matching: %s", exc)
        return False

    # 5.2 Fuzzy product matching
    match_results = _nlp_parser.match_products(items, store_products)

    # 5.3.1 Detect ambiguous / not-found items
    not_found = [r for r in match_results if r["status"] == "not_found"]
    ambiguous = [r for r in match_results if r["status"] == "ambiguous"]
    matched = [r for r in match_results if r["status"] == "matched"]

    if not_found:
        names = ", ".join(r["item"]["product"] for r in not_found)
        await update.message.reply_text(
            f"❌ I couldn't find these products: *{names}*\n\n"
            "Please check the product name or use 📦 View Products to see what's available.",
            parse_mode="Markdown",
        )
        return True

    if ambiguous:
        # 5.3.2 Ask clarifying question for first ambiguous item
        first = ambiguous[0]
        options = first["matches"][:5]  # max 5 options
        remaining_ambiguous = ambiguous[1:]
        remaining_matched = matched

        # Build inline keyboard
        keyboard = []
        for i, opt in enumerate(options, 1):
            p = opt["product"]
            label = f"{i}. {p['name']} — ₹{p['price']}/{p.get('unit', 'pcs')}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"nlp_pick_{i-1}")])

        _conv_manager.set_pending_clarification(user_id, {
            "item": first["item"],
            "options": [o["product"] for o in options],
            "remaining_items": [r["matches"][0]["product"] for r in remaining_matched],
            "remaining_ambiguous": remaining_ambiguous,
        })

        product_name = first["item"]["product"]
        await update.message.reply_text(
            f"🤔 I found multiple products matching *{product_name}*. Which one do you want?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return True

    # All matched — build cart and show confirmation
    cart_items = []
    for result in matched:
        product = result["matches"][0]["product"]
        item = result["item"]
        cart_items.append({
            "product_id": product.get("product_id"),
            "product_name": product.get("name"),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", product.get("unit", "pcs")),
            "unit_price": product.get("price", 0),
        })
        _conv_manager.add_to_cart(user_id, cart_items[-1])

    # 5.5.1 "Same as last time?" — offer for repeat customers
    last_order = _conv_manager.get_last_order_suggestion(customer["id"], supabase)
    same_as_last_btn = []
    if last_order:
        same_as_last_btn = [[InlineKeyboardButton("🔄 Same as last time?", callback_data="nlp_same_as_last")]]

    # Show order confirmation (5.6.3)
    cart = _conv_manager.get_cart(user_id)
    summary = _conv_manager.format_cart_summary(cart)
    _conv_manager.set_state(user_id, STATE_CONFIRMING)

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm (Cash)", callback_data="nlp_confirm_cash"),
            InlineKeyboardButton("💳 Confirm (Credit)", callback_data="nlp_confirm_credit"),
        ],
        [InlineKeyboardButton("✏️ Modify Order", callback_data="nlp_modify")],
        [InlineKeyboardButton("❌ Cancel", callback_data="nlp_cancel")],
    ] + same_as_last_btn

    await update.message.reply_text(
        f"{summary}\n\nHow would you like to pay?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return True


async def _handle_clarification_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    store_id: str,
    customer: dict,
    text: str,
) -> bool:
    """5.3.3 Handle user selection for ambiguous product."""
    clarification = _conv_manager.get_pending_clarification(user_id)
    if not clarification:
        _conv_manager.set_state(user_id, STATE_BROWSING)
        return False

    options = clarification.get("options", [])
    # Try to parse a number from the text
    match = re.search(r"\b([1-9])\b", text)
    if not match:
        await update.message.reply_text(
            "Please reply with a number to select the product, e.g. *1* or *2*.",
            parse_mode="Markdown",
        )
        return True

    choice_idx = int(match.group(1)) - 1
    if choice_idx < 0 or choice_idx >= len(options):
        await update.message.reply_text(f"Please enter a number between 1 and {len(options)}.")
        return True

    selected_product = options[choice_idx]
    item = clarification["item"]

    _conv_manager.add_to_cart(user_id, {
        "product_id": selected_product.get("product_id"),
        "product_name": selected_product.get("name"),
        "quantity": item.get("quantity", 1),
        "unit": item.get("unit", selected_product.get("unit", "pcs")),
        "unit_price": selected_product.get("price", 0),
    })
    _conv_manager.clear_pending_clarification(user_id)

    # Check if more ambiguous items remain
    remaining_ambiguous = clarification.get("remaining_ambiguous", [])
    if remaining_ambiguous:
        next_ambiguous = remaining_ambiguous[0]
        options_next = next_ambiguous["matches"][:5]
        keyboard = []
        for i, opt in enumerate(options_next, 1):
            p = opt["product"]
            label = f"{i}. {p['name']} — ₹{p['price']}/{p.get('unit', 'pcs')}"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"nlp_pick_{i-1}")])

        _conv_manager.set_pending_clarification(user_id, {
            "item": next_ambiguous["item"],
            "options": [o["product"] for o in options_next],
            "remaining_items": clarification.get("remaining_items", []),
            "remaining_ambiguous": remaining_ambiguous[1:],
        })
        product_name = next_ambiguous["item"]["product"]
        await update.message.reply_text(
            f"Got it! Now, which *{product_name}* did you want?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return True

    # All resolved — show cart confirmation
    cart = _conv_manager.get_cart(user_id)
    summary = _conv_manager.format_cart_summary(cart)
    _conv_manager.set_state(user_id, STATE_CONFIRMING)

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm (Cash)", callback_data="nlp_confirm_cash"),
            InlineKeyboardButton("💳 Confirm (Credit)", callback_data="nlp_confirm_credit"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="nlp_cancel")],
    ]
    await update.message.reply_text(
        f"{summary}\n\nHow would you like to pay?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return True


async def handle_nlp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle NLP-related inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    data = query.data

    if user_id not in user_sessions or "store_id" not in user_sessions[user_id]:
        await query.edit_message_text("⚠️ Session expired. Please /start again.")
        return

    store_id = user_sessions[user_id]["store_id"]
    customer = await get_customer_data(user_id, store_id)
    if not customer:
        await query.edit_message_text("❌ Profile not found.")
        return

    # 5.3.3 Product selection from ambiguity resolution
    if data.startswith("nlp_pick_"):
        idx = int(data.split("_")[-1])
        clarification = _conv_manager.get_pending_clarification(user_id)
        if not clarification:
            await query.edit_message_text("⚠️ Session expired.")
            return

        options = clarification.get("options", [])
        if idx >= len(options):
            await query.edit_message_text("Invalid selection.")
            return

        selected_product = options[idx]
        item = clarification["item"]
        _conv_manager.add_to_cart(user_id, {
            "product_id": selected_product.get("product_id"),
            "product_name": selected_product.get("name"),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", selected_product.get("unit", "pcs")),
            "unit_price": selected_product.get("price", 0),
        })
        _conv_manager.clear_pending_clarification(user_id)

        remaining_ambiguous = clarification.get("remaining_ambiguous", [])
        if remaining_ambiguous:
            next_item = remaining_ambiguous[0]
            options_next = next_item["matches"][:5]
            keyboard = []
            for i, opt in enumerate(options_next, 1):
                p = opt["product"]
                label = f"{i}. {p['name']} — ₹{p['price']}/{p.get('unit', 'pcs')}"
                keyboard.append([InlineKeyboardButton(label, callback_data=f"nlp_pick_{i-1}")])
            _conv_manager.set_pending_clarification(user_id, {
                "item": next_item["item"],
                "options": [o["product"] for o in options_next],
                "remaining_items": clarification.get("remaining_items", []),
                "remaining_ambiguous": remaining_ambiguous[1:],
            })
            product_name = next_item["item"]["product"]
            await query.edit_message_text(
                f"Got it! Now, which *{product_name}* did you want?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        # Show cart confirmation
        cart = _conv_manager.get_cart(user_id)
        summary = _conv_manager.format_cart_summary(cart)
        _conv_manager.set_state(user_id, STATE_CONFIRMING)
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm (Cash)", callback_data="nlp_confirm_cash"),
                InlineKeyboardButton("💳 Confirm (Credit)", callback_data="nlp_confirm_credit"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="nlp_cancel")],
        ]
        await query.edit_message_text(
            f"{summary}\n\nHow would you like to pay?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # 5.5.1 Same as last time
    if data == "nlp_same_as_last":
        last_items = _conv_manager.get_last_order_suggestion(customer["id"], supabase)
        if not last_items:
            await query.edit_message_text("No previous order found.")
            return
        _conv_manager.clear_cart(user_id)
        for item in last_items:
            _conv_manager.add_to_cart(user_id, {
                "product_id": item.get("product_id"),
                "product_name": item.get("product_name"),
                "quantity": item.get("quantity", 1),
                "unit_price": item.get("unit_price", 0),
            })
        cart = _conv_manager.get_cart(user_id)
        summary = _conv_manager.format_cart_summary(cart)
        _conv_manager.set_state(user_id, STATE_CONFIRMING)
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm (Cash)", callback_data="nlp_confirm_cash"),
                InlineKeyboardButton("💳 Confirm (Credit)", callback_data="nlp_confirm_credit"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="nlp_cancel")],
        ]
        await query.edit_message_text(
            f"🔄 *Same as last time:*\n\n{summary}\n\nHow would you like to pay?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Confirm order (cash or credit)
    if data in ("nlp_confirm_cash", "nlp_confirm_credit"):
        is_credit = data == "nlp_confirm_credit"
        cart = _conv_manager.get_cart(user_id)
        if not cart:
            await query.edit_message_text("Your cart is empty.")
            return

        # Credit enforcement check
        if is_credit:
            try:
                credit_data = supabase.table("customers")\
                    .select("credit_limit, credit_suspended, credit_score")\
                    .eq("id", customer["id"]).single().execute().data or {}
                credit_limit = float(credit_data.get("credit_limit") or 0)
                credit_suspended = bool(credit_data.get("credit_suspended", False))

                if credit_suspended:
                    await query.edit_message_text(
                        "❌ Your credit is suspended. Please pay with cash or clear your balance.",
                        parse_mode="Markdown",
                    )
                    return

                total = sum(float(i.get("unit_price", 0)) * float(i.get("quantity", 1)) for i in cart)
                outstanding_result = supabase.table("orders")\
                    .select("total_amount")\
                    .eq("customer_id", customer["id"])\
                    .eq("payment_status", "unpaid")\
                    .eq("is_credit", True).execute()
                outstanding = sum(float(o.get("total_amount", 0)) for o in (outstanding_result.data or []))
                available_credit = credit_limit - outstanding

                if credit_limit == 0:
                    await query.edit_message_text("❌ Credit not available. Please pay with cash.")
                    return
                if total > available_credit:
                    await query.edit_message_text(
                        f"❌ Credit limit exceeded.\nOrder: ₹{total:.0f} | Available: ₹{available_credit:.0f}\n"
                        "Please pay with cash or reduce your order.",
                        parse_mode="Markdown",
                    )
                    return
            except Exception as exc:
                logger.warning("Credit check error (allowing order): %s", exc)

        # Place the order via customer service
        order_data = {
            "customer_phone": customer["phone"],
            "items": [
                {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                }
                for item in cart
            ],
            "is_credit": is_credit,
        }

        try:
            async with httpx.AsyncClient() as client:
                order_response = await client.post(
                    f"{CUSTOMER_SERVICE_URL}/api/customer/order/{store_id}",
                    json=order_data,
                    timeout=10.0,
                )
                order_result = order_response.json()

            if order_result.get("success"):
                payment_label = "💳 Credit (Pay Later)" if is_credit else "💵 Cash on Delivery"
                total = sum(float(i.get("unit_price", 0)) * float(i.get("quantity", 1)) for i in cart)
                _conv_manager.clear_cart(user_id)
                _conv_manager.set_state(user_id, STATE_CONFIRMED)
                await query.edit_message_text(
                    f"✅ *Order Placed Successfully!*\n\n"
                    f"Order ID: `{order_result['order_id'][:8]}...`\n"
                    f"Total: ₹{total:.0f}\n"
                    f"Payment: {payment_label}\n\n"
                    f"{'⏳ Your order will be delivered soon!' if not is_credit else '💳 Pay when convenient!'}",
                    parse_mode="Markdown",
                )
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="What else can I help you with?",
                    reply_markup=get_main_menu(),
                )
            else:
                await query.edit_message_text(f"❌ {order_result.get('message', 'Order failed')}")
        except Exception as exc:
            logger.error("NLP order placement error: %s", exc)
            await query.edit_message_text("❌ Error placing order. Please try again.")
        return

    # 5.5.3 Modify order
    if data == "nlp_modify":
        cart = _conv_manager.get_cart(user_id)
        if not cart:
            await query.edit_message_text("Your cart is empty.")
            return
        lines = ["✏️ *Modify your order:*\n"]
        for i, item in enumerate(cart, 1):
            lines.append(f"{i}. {item.get('product_name')} — {item.get('quantity')} {item.get('unit', 'pcs')}")
        lines.append("\nType the item number and new quantity, e.g. *1 3* to change item 1 to quantity 3.")
        lines.append("Type *0* to remove an item.")
        _conv_manager.set_state(user_id, STATE_ORDERING)
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return

    # Cancel
    if data == "nlp_cancel":
        _conv_manager.clear_cart(user_id)
        _conv_manager.set_state(user_id, STATE_BROWSING)
        await query.edit_message_text("❌ Order cancelled.")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="No problem! What else can I help you with?",
            reply_markup=get_main_menu(),
        )
        return


# ---------------------------------------------------------------------------
# Handle messages (5.6.1 NLP first, fallback to command-based)
# ---------------------------------------------------------------------------

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "📦" in text or "view products" in text.lower():
        await view_products(update, context)
        return
    elif "👤" in text or "my profile" in text.lower():
        await view_profile(update, context)
        return
    elif "🏪" in text or "my stores" in text.lower():
        await view_stores(update, context)
        return
    elif "📋" in text or "my orders" in text.lower():
        await view_orders(update, context)
        return
    elif "🛍️" in text or "place order" in text.lower():
        # 5.5.2 "Your usual order?" suggestion for repeat customers
        user_id = update.effective_user.id
        if NLP_ENABLED and _conv_manager and user_id in user_sessions:
            store_id = user_sessions[user_id].get("store_id")
            if store_id:
                customer = await get_customer_data(user_id, store_id)
                if customer:
                    usual = _conv_manager.get_usual_order(customer["id"], supabase)
                    if usual:
                        names = ", ".join(u.get("product_name", "") for u in usual)
                        keyboard = [
                            [InlineKeyboardButton(f"🔄 Order usual: {names}", callback_data="nlp_same_as_last")],
                        ]
                        await update.message.reply_text(
                            "💬 Just tell me what you need! For example:\n"
                            "*\"2kg rice and 1kg sugar\"*\n\n"
                            "Or order your usual:",
                            parse_mode="Markdown",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                        return

        await update.message.reply_text(
            "💬 Just tell me what you need! For example:\n"
            "*\"2kg rice and 1kg sugar\"*\n\n"
            "Or use the command: `order <product> <quantity>`",
            parse_mode="Markdown",
        )
        return
    elif "🔙" in text or "back" in text.lower():
        await update.message.reply_text("Main menu:", reply_markup=get_main_menu())
        return

    # 5.6.1 Try NLP first for free-text messages
    if NLP_ENABLED:
        try:
            handled = await handle_nlp_message(update, context)
            if handled:
                return
        except Exception as exc:
            logger.error("NLP handler error (falling back): %s", exc)

    # 5.9 Fallback to command-based ordering
    if text.lower().startswith("order "):
        await place_order(update, context)
    else:
        await update.message.reply_text(
            "💬 Just tell me what you need in plain language!\n"
            "Example: *\"2kg rice and 1kg sugar\"*\n\n"
            "Or try:\n"
            "• 📦 View Products\n"
            "• 🛍️ Place Order\n"
            "• 📋 My Orders\n"
            "• 👤 My Profile",
            parse_mode="Markdown",
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
            ASKING_BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthday)],
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
    application.add_handler(CallbackQueryHandler(handle_nlp_callback, pattern="^nlp_"))
    application.add_handler(CallbackQueryHandler(handle_payment_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot is running!")
    print("📱 Share: https://t.me/BazaarOpsCustomerHelpBot?start=STORE_ID")
    print("Press Ctrl+C to stop")
    
    application.run_polling()

if __name__ == "__main__":
    main()

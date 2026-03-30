import asyncio
from datetime import datetime, timezone
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from pathlib import Path

# Conversation state for quantity editing
AWAITING_QUANTITY = 1

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


# ---------------------------------------------------------------------------
# Reorder approval callbacks (2.3.2 - 2.3.3)
# ---------------------------------------------------------------------------

async def reorder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Approve / Edit / Reject inline button callbacks for reorders."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("reorder_"):
        return

    parts = data.split(":", 1)
    if len(parts) != 2:
        return

    action, reorder_id = parts[0].replace("reorder_", ""), parts[1]

    if action == "approve":
        success = await _approve_reorder(reorder_id)
        if success:
            await query.edit_message_text(
                f"✅ *Reorder Approved!*\n\nReorder `{reorder_id[:8]}` has been approved. "
                f"Supplier will be contacted.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("❌ Failed to approve reorder. Please try again.")

    elif action == "reject":
        success = await _reject_reorder(reorder_id)
        if success:
            await query.edit_message_text(
                f"❌ *Reorder Rejected*\n\nReorder `{reorder_id[:8]}` has been rejected.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("❌ Failed to reject reorder. Please try again.")

    elif action == "edit":
        # Store reorder_id in user context and ask for new quantity
        context.user_data["editing_reorder_id"] = reorder_id
        await query.edit_message_text(
            f"✏️ *Edit Quantity*\n\nPlease reply with the new quantity for reorder `{reorder_id[:8]}`:",
            parse_mode="Markdown",
        )
        return AWAITING_QUANTITY


async def receive_edited_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the owner's reply with a new quantity (2.3.3)."""
    reorder_id = context.user_data.get("editing_reorder_id")
    if not reorder_id:
        await update.message.reply_text("❌ No active reorder edit session.")
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    try:
        new_qty = float(text)
        if new_qty <= 0:
            raise ValueError("Quantity must be positive")
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid quantity. Please enter a positive number."
        )
        return AWAITING_QUANTITY

    success = await _approve_reorder(reorder_id, approved_quantity=new_qty)
    if success:
        await update.message.reply_text(
            f"✅ *Reorder Updated & Approved!*\n\n"
            f"Quantity set to *{new_qty:.1f}* for reorder `{reorder_id[:8]}`.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Failed to update reorder. Please try again.")

    context.user_data.pop("editing_reorder_id", None)
    return ConversationHandler.END


async def _approve_reorder(reorder_id: str, approved_quantity: float | None = None) -> bool:
    """Approve a reorder via Supabase (2.3.4)."""
    try:
        result = (
            supabase.table("pending_supplier_orders")
            .select("id, quantity")
            .eq("id", reorder_id)
            .single()
            .execute()
        )
        if not result.data:
            return False

        suggested_qty = float(result.data["quantity"])
        final_qty = approved_quantity if approved_quantity is not None else suggested_qty

        supabase.table("pending_supplier_orders").update(
            {
                "owner_approved": True,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "quantity": final_qty,
                "status": "approved",
            }
        ).eq("id", reorder_id).execute()

        # Record for learning system
        owner_edited = abs(final_qty - suggested_qty) > 0.01
        edit_pct = (
            ((final_qty - suggested_qty) / suggested_qty * 100)
            if suggested_qty > 0
            else 0.0
        )
        supabase.table("reorder_approvals").insert(
            {
                "reorder_id": reorder_id,
                "suggested_quantity": suggested_qty,
                "approved_quantity": final_qty,
                "owner_edited": owner_edited,
                "edit_percentage": round(edit_pct, 2),
            }
        ).execute()

        print(f"✅ Reorder {reorder_id[:8]} approved (qty={final_qty})")
        return True
    except Exception as e:
        print(f"❌ _approve_reorder error: {e}")
        return False


async def _reject_reorder(reorder_id: str) -> bool:
    """Reject a reorder via Supabase."""
    try:
        supabase.table("pending_supplier_orders").update(
            {"status": "rejected", "owner_approved": False}
        ).eq("id", reorder_id).execute()
        print(f"✅ Reorder {reorder_id[:8]} rejected")
        return True
    except Exception as e:
        print(f"❌ _reject_reorder error: {e}")
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

        # Reorder approval conversation handler (Edit Quantity flow)
        reorder_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(reorder_callback, pattern=r"^reorder_")],
            states={
                AWAITING_QUANTITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited_quantity)
                ],
            },
            fallbacks=[],
            per_user=True,
            per_chat=True,
        )
        application.add_handler(reorder_conv)

        # Standalone callback handler for approve/reject (no conversation needed)
        application.add_handler(
            CallbackQueryHandler(reorder_callback, pattern=r"^reorder_(approve|reject):")
        )
        
        print("\n🚀 Bot is running...")
        print("📱 Commands:")
        print("  • /start - Auto-link your store")
        print("  • /register <phone> - Manual registration")
        print("  • /status - Check your stats")
        print("\n🧠 AI Agents handle:")
        print("  • Intelligent inventory analysis")
        print("  • Credit risk assessment")
        print("  • Daily business insights")
        print("  • Reorder approvals (Approve/Edit/Reject)")
        print("\nPress Ctrl+C to stop\n")
        
        # Run bot - simple polling
        application.run_polling()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

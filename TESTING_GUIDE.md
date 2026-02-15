# 🧪 BazaarOps - Complete Testing Guide

## 🚀 Step-by-Step Testing

### 1. Start All Services

```bash
python main.py
```

**Expected Output:**
```
✅ Started: Owner-Service (Port 8001)
✅ Started: Customer-Service (Port 8002)
✅ Started: Agent-Service (Port 8003)
✅ Started: NextJS-Dashboard (Port 3000)
✅ Started: Owner-Bot (@BazaarOpsAdminBot)
✅ Started: Customer-Bot (@BazaarOpsCustomerHelpBot)
✅ Started: Claude-AI-Scheduler
```

---

### 2. Owner Side Testing

#### A. Register as Owner
1. Open browser: `http://localhost:3000/auth`
2. Fill registration form:
   - Email: `test@shop.com`
   - Password: `Test@123`
   - Shop Name: `My Test Shop`
   - Phone: `9876543210`
   - Telegram Username: `your_telegram_username` (without @)
   - Address: `123 Test Street`
3. Click "Register"
4. Note your `store_id` (saved in localStorage)

#### B. Link Telegram Bot
1. Open Telegram
2. Search: `@BazaarOpsAdminBot`
3. Send: `/start`
4. Bot should auto-link and send welcome message

**Expected Message:**
```
🎉 Welcome to BazaarOps Admin! 🎉

Hello My Test Shop! 👋

✅ Your store is now linked!

🔔 You'll now receive:
• Real-time low stock alerts
• Daily sales reports at 9 PM
• Credit analysis
• Order notifications
```

#### C. Add Inventory
1. Login to dashboard: `http://localhost:3000`
2. Go to "Inventory" page
3. Click "Add Category"
   - Name: `Groceries`
4. Click "Add Product"
   - Name: `Rice`
   - Category: `Groceries`
   - Price: `50`
   - Unit: `kg`
   - Quantity: `100`
   - Reorder Threshold: `20`
5. Product should appear in inventory table

#### D. Get Customer Bot Link
1. Go to "Settings" page
2. Find "Customer Shopping Bot" section
3. Copy the link: `https://t.me/BazaarOpsCustomerHelpBot?start=YOUR_STORE_ID`
4. This is your unique customer link!

---

### 3. Customer Side Testing

#### A. Customer Opens Bot
1. Open the customer link in Telegram (or send to another phone)
2. Bot should start automatically with your store context
3. Customer sees menu:
   - 📦 View Products
   - 🛍️ Place Order
   - 📋 My Orders

#### B. View Products
1. Click "📦 View Products"
2. Bot shows all available products:
```
📦 Available Products:

1. Rice
   ₹50/kg
   Available: 100 kg
```

#### C. Place Order
1. Type: `order Rice 2`
2. Bot processes order
3. Bot confirms:
```
✅ Order Placed!

Product: Rice
Quantity: 2 kg
Price: ₹50/kg
Total: ₹100

Order ID: abc123...

Store will confirm soon!
```

#### D. Check Inventory Reduction
1. Go back to owner dashboard
2. Check Inventory page
3. Rice quantity should be: `98 kg` (100 - 2)

---

### 4. Order Management Testing

#### A. View Orders
1. Owner dashboard → "Orders" page
2. See the new order from customer
3. Status should be "Confirmed" (auto-confirmed if stock available)

#### B. Mark as Delivered
1. Click "Mark as Delivered" button
2. Order status changes to "Completed"
3. Customer receives auto-notification on Telegram:
```
✅ Your order has been delivered!

Thank you for shopping with us! 🎉
```

---

### 5. Promotional Message Testing

#### A. Send Promo
1. Owner dashboard → "Settings" page
2. Scroll to "Send Promotional Message" section
3. Enter message:
```
🎉 Special Offer! 🎉

Get 20% off on all products today!

Order now: https://t.me/BazaarOpsCustomerHelpBot?start=YOUR_STORE_ID
```
4. Click "Send to All Customers"
5. All customers with Telegram receive the message

---

### 6. AI Agents Testing

#### A. Manual Trigger (for testing)
You can manually trigger AI agents:

**Inventory Analysis:**
```bash
cd telegram-bots/owner-bot
python -c "from agents.intelligent_restocking_agent import analyze_inventory_with_ai; import asyncio; asyncio.run(analyze_inventory_with_ai('YOUR_STORE_ID'))"
```

**Daily Report:**
```bash
cd telegram-bots/owner-bot
python -c "from agents.daily_report_agent import generate_daily_report; import asyncio; asyncio.run(generate_daily_report('YOUR_STORE_ID'))"
```

**Credit Analysis:**
```bash
cd telegram-bots/owner-bot
python -c "from agents.intelligent_credit_agent import analyze_credit_with_ai; import asyncio; asyncio.run(analyze_credit_with_ai('YOUR_STORE_ID'))"
```

#### B. Scheduled Execution
AI agents run automatically:
- **10:00 AM** - Inventory Analysis
- **04:00 PM** - Inventory Analysis
- **09:00 PM** - Daily Report
- **09:05 PM** - Credit Analysis

---

### 7. Complete End-to-End Flow

**Scenario: New Customer Orders**

1. ✅ Owner shares customer bot link via WhatsApp
2. ✅ Customer clicks link → Bot opens with store context
3. ✅ Customer views products
4. ✅ Customer places order: `order Rice 5`
5. ✅ Inventory automatically reduces (100 → 95)
6. ✅ Order appears in owner dashboard (status: Confirmed)
7. ✅ Owner delivers product
8. ✅ Owner marks as "Delivered" in dashboard
9. ✅ Customer gets auto-notification on Telegram
10. ✅ At 9 PM, owner gets AI-powered daily report

---

## 🐛 Troubleshooting

### Issue: Bot not responding
**Solution:**
```bash
# Check if bot token is correct in .env
cat .env | grep BOT_TOKEN

# Restart services
python main.py
```

### Issue: Inventory not reducing
**Solution:**
- Check database triggers are installed (from previous setup)
- Verify order status is "confirmed"

### Issue: Customer bot link not working
**Solution:**
- Verify `store_id` is correct
- Check customer bot is running
- Ensure bot token is valid

### Issue: AI agents not working
**Solution:**
```bash
# Check Anthropic API key
cat .env | grep ANTHROPIC

# Verify anthropic package installed
pip list | grep anthropic
```

---

## ✅ Success Checklist

- [ ] All 7 services running
- [ ] Owner registered and logged in
- [ ] Owner bot linked via Telegram
- [ ] Inventory added (categories + products)
- [ ] Customer bot link copied
- [ ] Customer placed order via bot
- [ ] Inventory reduced automatically
- [ ] Order visible in dashboard
- [ ] Order marked as delivered
- [ ] Customer received notification
- [ ] Promotional message sent
- [ ] AI agents can be triggered manually

---

## 📊 Expected Database State After Testing

**stores table:**
- 1 store with telegram_chat_id linked

**products table:**
- At least 1 product (Rice)

**categories table:**
- At least 1 category (Groceries)

**inventory table:**
- Rice: quantity reduced from 100 to 95

**orders table:**
- 1 order with status "completed"

**order_items table:**
- 1 item (Rice, quantity 5)

**customers table:**
- 1 customer with telegram_chat_id

---

## 🎯 Next Steps After Testing

1. Add more products and categories
2. Test with multiple customers
3. Wait for scheduled AI reports (9 PM)
4. Test credit orders (is_credit=true)
5. Test low stock alerts (reduce inventory below threshold)
6. Share customer link with real customers!

---

**Happy Testing! 🚀**

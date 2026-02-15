# 🛒 BazaarOps - AI-Powered Store Management System

A comprehensive store management platform with AI-powered inventory insights, Telegram bot integration, and real-time order tracking.

## 🌟 Features

### 📱 Telegram Bots
- **Owner Bot** (@BazaarOpsAdminBot)
  - Daily business reports at 9 PM
  - AI-powered inventory analysis (10 AM & 4 PM)
  - Intelligent credit risk assessment (9:05 PM)
  - Real-time notifications

- **Customer Bot** (@BazaarOpsCustomerHelpBot)
  - Deep linking with store-specific onboarding
  - Easy product browsing and ordering
  - Order tracking with status updates
  - Profile management (name, phone, address)
  - Multi-store support

### 💼 Owner Dashboard
- **Real-time Analytics**
  - Today's orders, revenue, and profit
  - Low stock alerts
  - Customer insights

- **Inventory Management**
  - Add/edit products and categories
  - Live stock updates
  - Reorder threshold tracking
  - WhatsApp supplier integration for low stock items

- **Order Management**
  - Automatic order confirmation (stock-based)
  - Mark as delivered with customer notifications
  - Order history and filtering

- **Customer Management**
  - View all customers
  - Send promotional messages via Telegram
  - Template-based messaging with Markdown support

- **Settings**
  - Owner & Customer bot links
  - Shareable customer bot link with store ID
  - Promotional message templates

### 🤖 AI-Powered Features
- **Intelligent Restocking Agent**
  - Analyzes sales velocity and stock levels
  - Predicts reorder needs
  - Runs twice daily (10 AM & 4 PM)

- **Credit Risk Assessment**
  - Evaluates customer payment patterns
  - Identifies high-risk credit customers
  - Daily analysis at 9:05 PM

- **Daily Business Reports**
  - Comprehensive end-of-day summaries
  - Revenue and order insights
  - Delivered at 9 PM daily

## 🏗️ Architecture

```
BazaarOps/
├── owner-dashboard/          # Next.js 14 (App Router)
├── owner-service/            # FastAPI - Owner operations
├── customer-service/         # FastAPI - Customer operations
├── agent-service/            # FastAPI - Event handling
├── telegram-bots/
│   ├── owner-bot/           # Owner Telegram bot
│   └── customer-bot/        # Customer Telegram bot
├── .env                     # Unified configuration
├── requirements.txt         # Python dependencies
└── main.py                  # Unified startup script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- Supabase account
- Telegram Bot tokens (from @BotFather)
- Anthropic API key (for AI features)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd BazaarOps
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Install Node.js dependencies**
```bash
cd owner-dashboard
npm install
cd ..
```

4. **Configure environment variables**

Create `.env` in the root directory:
```env
# Database (Supabase)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key

# Telegram Bots
OWNER_BOT_TOKEN=your_owner_bot_token
CUSTOMER_BOT_TOKEN=your_customer_bot_token

# AI Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key

# Service URLs
OWNER_SERVICE_URL=http://localhost:8001
CUSTOMER_SERVICE_URL=http://localhost:8002
AGENT_SERVICE_URL=http://localhost:8003
```

Create `owner-dashboard/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
TELEGRAM_BOT_TOKEN=your_owner_bot_token
NEXT_PUBLIC_TELEGRAM_BOT_TOKEN=your_owner_bot_token
NEXT_PUBLIC_CUSTOMER_BOT_TOKEN=your_customer_bot_token
```

5. **Build the dashboard**
```bash
cd owner-dashboard
npm run build
cd ..
```

6. **Start all services**
```bash
python main.py
```

This will start:
- Owner Service (Port 8001)
- Customer Service (Port 8002)
- Agent Service (Port 8003)
- Next.js Dashboard (Port 3000)
- Owner Telegram Bot
- Customer Telegram Bot
- AI Scheduler (Background)

## 📊 Database Setup

### Required Tables

Run these SQL commands in Supabase SQL Editor:

```sql
-- Stores table
CREATE TABLE stores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  phone TEXT,
  address TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Categories table
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  category_id UUID REFERENCES categories(id),
  name TEXT NOT NULL,
  description TEXT,
  unit TEXT DEFAULT 'kg',
  cost_price DECIMAL(10,2) DEFAULT 0,
  supplier_name TEXT,
  supplier_phone TEXT,
  supplier_whatsapp TEXT,
  sales_velocity TEXT DEFAULT 'normal',
  created_at TIMESTAMP DEFAULT NOW()
);

-- Inventory table
CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  product_id UUID REFERENCES products(id),
  quantity DECIMAL(10,2) DEFAULT 0,
  unit_price DECIMAL(10,2) DEFAULT 0,
  reorder_threshold DECIMAL(10,2) DEFAULT 10,
  reorder_quantity DECIMAL(10,2) DEFAULT 20,
  last_restocked TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Customers table
CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  address TEXT,
  telegram_chat_id TEXT,
  telegram_username TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Orders table
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  customer_id UUID REFERENCES customers(id),
  total_amount DECIMAL(10,2) NOT NULL,
  status TEXT DEFAULT 'confirmed',
  payment_status TEXT DEFAULT 'paid',
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Order Items table
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID REFERENCES orders(id),
  product_id UUID REFERENCES products(id),
  product_name TEXT NOT NULL,
  quantity DECIMAL(10,2) NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Owners table
CREATE TABLE owners (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID REFERENCES stores(id),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  telegram_chat_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## 🎯 Usage

### For Store Owners

1. **Register/Login**
   - Visit `http://localhost:3000/auth`
   - Create account or login

2. **Setup Inventory**
   - Add categories
   - Add products with supplier details
   - Set reorder thresholds

3. **Share Customer Bot Link**
   - Go to Settings
   - Copy your unique customer bot link
   - Share with customers

4. **Manage Orders**
   - View confirmed orders
   - Mark as delivered (sends notification to customer)

5. **Monitor AI Insights**
   - Check Telegram for daily reports
   - Review inventory recommendations
   - Monitor credit risk alerts

### For Customers

1. **Start Shopping**
   - Click store's unique bot link
   - Complete onboarding (name, phone, address)

2. **Browse & Order**
   - View products
   - Place orders: `order Rice 2`
   - Track order status

3. **Manage Profile**
   - Edit name, phone, address
   - View order history
   - Check visited stores

## 🔧 Configuration

### AI Agent Schedule
Edit `telegram-bots/owner-bot/scheduler.py`:
```python
schedule.every().day.at("10:00").do(run_inventory_analysis)
schedule.every().day.at("16:00").do(run_inventory_analysis)
schedule.every().day.at("21:00").do(run_daily_report)
schedule.every().day.at("21:05").do(run_credit_analysis)
```

### Telegram Bot Commands

**Owner Bot:**
- `/start` - Initialize bot
- Receives automated reports

**Customer Bot:**
- `/start STORE_ID` - Register with store
- `order <product> <quantity>` - Place order
- Use menu buttons for navigation

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance Python web framework
- **Supabase** - PostgreSQL database with real-time features
- **Anthropic Claude** - AI-powered insights
- **python-telegram-bot** - Telegram bot integration

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Lucide Icons** - Beautiful icons

### AI & Automation
- **Claude 3.5 Sonnet** - Advanced AI model
- **Schedule** - Python job scheduling
- **HTTPX** - Async HTTP client

## 📱 Telegram Bot Setup

### Create Bots with @BotFather

1. **Owner Bot**
```
/newbot
Name: YourStore Admin Bot
Username: YourStoreAdminBot
```

2. **Customer Bot**
```
/newbot
Name: YourStore Customer Bot
Username: YourStoreCustomerBot
```

Save the tokens in `.env` file.

## 🔐 Security

- Service role keys for backend operations
- Anon keys for frontend (limited access)
- Password hashing for owner accounts
- Environment-based configuration
- No sensitive data in git

## 📈 Profit Calculation

Profit = Revenue - Cost

- **Revenue**: Sum of all order totals
- **Cost**: Sum of (product cost_price × quantity) for all order items
- Displayed on dashboard for today's orders

## 🎨 Customization

### Add New Product Units
Edit `owner-dashboard/app/inventory/page.tsx`:
```tsx
<option value="kg">Kg</option>
<option value="liter">Liter</option>
<option value="piece">Piece</option>
<option value="box">Box</option>
<option value="dozen">Dozen</option> // Add new
```

### Modify AI Agent Prompts
Edit files in `telegram-bots/owner-bot/agents/`:
- `intelligent_restocking_agent.py`
- `intelligent_credit_agent.py`
- `daily_report_agent.py`

## 🐛 Troubleshooting

### Services won't start
```bash
# Check if ports are in use
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8003
netstat -ano | findstr :3000
```

### Telegram messages not sending
- Verify bot tokens in `.env` and `.env.local`
- Check customer has `telegram_chat_id` in database
- Restart services after env changes

### Database connection issues
- Verify Supabase URL and keys
- Check network connectivity
- Ensure tables are created

### AI features not working
- Verify Anthropic API key
- Check API quota/limits
- Review scheduler logs

## 📝 License

MIT License - feel free to use for your projects!

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 Support

For issues and questions:
- Open a GitHub issue
- Check existing documentation
- Review error logs in console

## 🎉 Acknowledgments

- Built with Claude AI assistance
- Powered by Supabase
- Telegram Bot API
- Next.js team for amazing framework

---

**Made with ❤️ for small business owners**

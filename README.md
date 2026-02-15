# 🛒 BazaarOps - AI-Powered Store Management System

Complete store management platform with **Claude 3.5 Sonnet AI Agents** for intelligent automation, predictive analytics, and real-time business insights.

## 🧠 Claude AI Agents (Core Intelligence)

### 1. Intelligent Inventory Analyst
**File**: `intelligent_restocking_agent.py`
- Analyzes 30-day sales patterns and velocity
- Predicts demand using historical data
- Identifies fast-moving vs slow-moving items
- Provides cost-effective restocking recommendations
- Sends critical alerts with WhatsApp supplier links
- **Schedule**: 10:00 AM, 4:00 PM daily

### 2. AI Credit Risk Assessor
**File**: `intelligent_credit_agent.py`
- Evaluates payment patterns and customer behavior
- Assigns risk levels (High/Medium/Low)
- Generates personalized collection strategies
- Prioritizes follow-ups based on risk
- Suggests payment plans and communication approaches
- **Schedule**: 9:05 PM daily (only if credit exists)

### 3. AI Business Insights Generator
**File**: `daily_report_agent.py`
- Analyzes daily performance metrics
- Provides performance assessment (good/average/needs improvement)
- Highlights top categories and products
- Calculates profit margins and trends
- Delivers actionable recommendations for next day
- **Schedule**: 9:00 PM daily

## ✨ Key Features

### For Owners
- 📊 Real-time inventory tracking
- 🤖 AI-powered demand prediction
- 💳 Intelligent credit management
- 📱 Telegram notifications & insights
- 📈 Daily AI business reports
- 🔗 WhatsApp supplier integration
- 👥 Customer order management

### Technical Features
- Single-command startup (`python main.py`)
- Multi-store support (unique store_id per owner)
- Auto-linking via Telegram username
- Secure authentication with password validation
- RESTful API with FastAPI
- Modern React dashboard with TypeScript
- PostgreSQL database via Supabase

## 🚀 Quick Start

### Prerequisites
- Python 3.13+ (or 3.8+)
- Node.js 16+
- Supabase account
- **Claude API Key** (Get from https://console.anthropic.com/)
- Telegram Bot Tokens (Get from @BotFather)

### Installation

1. **Clone & Install Dependencies**
```bash
# Install ALL dependencies from root (unified requirements)
pip install -r requirements.txt

# Install Node.js dependencies for dashboard
cd owner-dashboard
npm install
cd ..
```

2. **Configure Environment Variables**

**Copy and configure the root .env file:**
```bash
cp .env.example .env
```

**Edit `.env` with your credentials:**
```env
# Database
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-service-role-key

# Telegram Bots
OWNER_BOT_TOKEN=your-owner-bot-token
CUSTOMER_BOT_TOKEN=your-customer-bot-token

# AI
ANTHROPIC_API_KEY=your-claude-api-key

# Service URLs (default - no need to change)
OWNER_SERVICE_URL=http://localhost:8001
CUSTOMER_SERVICE_URL=http://localhost:8002
AGENT_SERVICE_URL=http://localhost:8003
```

**Configure Dashboard `.env.local`:**
```bash
cd owner-dashboard
# Create .env.local with:
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
NEXT_PUBLIC_TELEGRAM_BOT_TOKEN=your_customer_bot_token
```

3. **Start Everything**
```bash
# Single command starts ALL services!
python main.py
```

This starts:
- ✅ Owner Service (Port 8001)
- ✅ Customer Service (Port 8002)
- ✅ Agent Service (Port 8003)
- ✅ Next.js Dashboard (Port 3000)
- ✅ Owner Bot (@BazaarOpsAdminBot)
- ✅ Customer Bot (@BazaarOpsCustomerHelpBot)
- ✅ Claude AI Agent Scheduler

## 📋 Complete Workflow

### Owner Side
1. **Owner Registration**
   - Visit http://localhost:3000/auth
   - Register with email, password, shop details
   - Provide phone number (with Telegram) and username

2. **Telegram Auto-Linking**
   - Open Telegram → Search @BazaarOpsAdminBot
   - Send `/start` command
   - Bot auto-links via your username
   - Receive welcome message

3. **Inventory Setup**
   - Login to dashboard
   - Create product categories
   - Add products with supplier details
   - Set reorder thresholds

4. **AI Automation Begins**
   - Claude analyzes your data
   - Sends intelligent insights via Telegram
   - Provides actionable recommendations
   - Monitors inventory 24/7

### Customer Side
1. **Owner Shares Link**
   - Owner gets unique link from Settings page
   - Format: `https://t.me/BazaarOpsCustomerHelpBot?start=STORE_ID`
   - Share with customers via WhatsApp/SMS

2. **Customer Orders**
   - Customer clicks link → Bot starts with store context
   - View products, place orders via Telegram
   - No manual store selection needed

3. **Order Processing**
   - Inventory automatically reduces
   - Owner sees order in dashboard
   - Owner marks as delivered
   - Customer gets auto-notification

## 🤖 Bot Commands

- `/start` - Auto-link your store (uses telegram_username)
- `/register <phone>` - Manual registration fallback
- `/status` - Check today's stats and bot status

## 🕐 AI Agent Schedule

| Time | Agent | Function |
|------|-------|----------|
| 10:00 AM | Inventory Analyst | Morning stock analysis & predictions |
| 04:00 PM | Inventory Analyst | Afternoon restock check |
| 09:00 PM | Business Insights | End-of-day performance report |
| 09:05 PM | Credit Assessor | Credit risk analysis & strategies |

## 🛠️ Tech Stack

### AI & Backend
- **AI**: Claude 3.5 Sonnet (Anthropic SDK)
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Bot**: python-telegram-bot
- **Scheduler**: schedule library

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide React
- **State**: React Hooks

## 📁 Project Structure

```
BazaarOps/
├── .env                             # 🔥 UNIFIED CONFIG (all services)
├── .env.example                     # Template for .env
├── requirements.txt                 # 🔥 UNIFIED REQUIREMENTS
├── main.py                          # Single entry point
│
├── owner-service/                   # Owner FastAPI backend (Port 8001)
│   ├── main.py
│   ├── routers/
│   └── services/
│
├── customer-service/                # Customer FastAPI backend (Port 8002)
│   ├── main.py
│   ├── routers/
│   └── services/
│
├── agent-service/                   # AI Agent service (Port 8003)
│   ├── main.py
│   ├── agents/
│   └── events/
│
├── owner-dashboard/                 # Next.js frontend (Port 3000)
│   ├── app/
│   │   ├── auth/                   # Authentication
│   │   ├── inventory/              # Inventory management
│   │   ├── orders/                 # Order tracking
│   │   ├── customers/              # Customer list
│   │   └── settings/               # Customer bot link generator
│   └── lib/
│
└── telegram-bots/
    ├── owner-bot/                   # Owner Telegram bot
    │   ├── bot.py
    │   ├── scheduler.py
    │   └── agents/                  # Claude AI agents
    │       ├── intelligent_restocking_agent.py
    │       ├── intelligent_credit_agent.py
    │       └── daily_report_agent.py
    │
    └── customer-bot/                # Customer Telegram bot
        └── bot.py                   # Deep linking support
```

## 🔒 Security

- Password validation (8+ chars, uppercase, lowercase, number, special)
- Service role key for backend operations
- Secure token-based authentication
- Environment variables for sensitive data
- RLS policies on Supabase tables

## 📊 Database Schema

Key tables:
- `stores` - Store information with telegram linking
- `users` - Owner accounts
- `products` - Product catalog with supplier info
- `inventory` - Stock levels and thresholds
- `orders` - Order tracking
- `order_items` - Order line items
- `customers` - Customer database

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] SMS notifications
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)
- [ ] Voice commands via Telegram
- [ ] Integration with accounting software

## 📝 License

MIT License

---

🧠 **Powered by Claude AI** | Made with ❤️ for small business owners

**Need Help?** Open an issue or contact support

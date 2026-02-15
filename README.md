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
- Python 3.8+
- Node.js 16+
- Supabase account
- **Claude API Key** (Get from https://console.anthropic.com/)

### Installation

1. **Clone & Install Dependencies**
```bash
# Install Python dependencies
cd owner-service
pip install -r requirements.txt
cd ..

cd telegram-bots/owner-bot
pip install -r requirements.txt
cd ../..

# Install Node.js dependencies
cd owner-dashboard
npm install
cd ..
```

2. **Configure Environment Variables**

**telegram-bots/owner-bot/.env**
```env
TELEGRAM_BOT_TOKEN=your_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key
ANTHROPIC_API_KEY=your_claude_api_key  # Required for AI agents
```

**owner-dashboard/.env.local**
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
TELEGRAM_BOT_TOKEN=your_bot_token
```

**owner-service/.env**
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_service_role_key
```

3. **Start Everything**
```bash
python main.py
```

This single command starts:
- ✅ FastAPI Backend (Port 8001)
- ✅ Next.js Dashboard (Port 3000)
- ✅ Telegram Bot (@BazaarOpsAdminBot)
- ✅ Claude AI Agent Scheduler

## 📋 Complete Workflow

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
├── main.py                          # Single entry point
├── owner-service/                   # FastAPI backend
│   ├── main.py
│   ├── routers/
│   └── services/
├── owner-dashboard/                 # Next.js frontend
│   ├── app/
│   │   ├── auth/                   # Authentication
│   │   ├── inventory/              # Inventory management
│   │   ├── orders/                 # Order tracking
│   │   └── customers/              # Customer list
│   └── lib/
└── telegram-bots/owner-bot/        # Telegram bot + AI agents
    ├── bot.py                      # Bot commands
    ├── scheduler.py                # AI agent scheduler
    └── agents/
        ├── intelligent_restocking_agent.py
        ├── intelligent_credit_agent.py
        └── daily_report_agent.py
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

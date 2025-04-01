# Local Setup — BazaarOps

> This guide covers running BazaarOps locally. Production deployment uses Render (backend + bots) and Vercel (dashboard) — see the Deployment section below.

---

## Prerequisites

- Python 3.13+
- Node.js 18+
- A Supabase project (free tier is sufficient)
- Two Telegram bots created via [@BotFather](https://t.me/BotFather)
- Anthropic API key (for AI features — [console.anthropic.com](https://console.anthropic.com))
- Redis instance (local `redis-server` or a managed Redis URL)

---

## 1. Clone and install

```bash
git clone https://github.com/tanisheesh/BazaarOps
cd BazaarOps
```

Install Python dependencies (shared across all services):

```bash
pip install -r requirements.txt
```

Install Node.js dependencies for the dashboard:

```bash
cd owner-dashboard
npm install
cd ..
```

---

## 2. Environment variables

Copy `.env.example` to `.env` at the project root and fill in the values:

```bash
cp .env.example .env
```

| Variable | Where to get it |
|---|---|
| `SUPABASE_URL` | Supabase project → Settings → API → Project URL |
| `SUPABASE_KEY` | Supabase project → Settings → API → service_role key (secret) |
| `OWNER_BOT_TOKEN` | @BotFather → `/newbot` → copy token |
| `CUSTOMER_BOT_TOKEN` | @BotFather → `/newbot` (second bot) → copy token |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `OWNER_SERVICE_URL` | `http://localhost:8001` for local dev |
| `CUSTOMER_SERVICE_URL` | `http://localhost:8002` for local dev |
| `AGENT_SERVICE_URL` | `http://localhost:8003` for local dev |
| `REDIS_URL` | `redis://localhost:6379` for local Redis |

Create `owner-dashboard/.env.local`:

```bash
cp owner-dashboard/.env.local.example owner-dashboard/.env.local  # if present
# or create manually:
```

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
TELEGRAM_BOT_TOKEN=your_owner_bot_token
NEXT_PUBLIC_TELEGRAM_BOT_TOKEN=your_owner_bot_token
NEXT_PUBLIC_CUSTOMER_BOT_TOKEN=your_customer_bot_token
```

Note: `NEXT_PUBLIC_SUPABASE_KEY` should be the **anon** key (safe for browser). `SUPABASE_SERVICE_KEY` is the service role key (server-side only, never `NEXT_PUBLIC_`).

---

## 3. Database setup

Run the SQL migration files in order in your Supabase SQL Editor (`supabase.com → your project → SQL Editor`):

```
agent-service/migrations/001_order_triggers.sql
agent-service/migrations/002_inventory_triggers.sql
agent-service/migrations/003_payment_triggers.sql
agent-service/migrations/004_event_log_table.sql
agent-service/migrations/005_reorder_tables.sql
agent-service/migrations/006_customer_lifecycle_tables.sql
agent-service/migrations/007_credit_tables.sql
agent-service/migrations/008_conversation_context.sql
agent-service/migrations/009_agent_collaboration_tables.sql
agent-service/migrations/010_notification_tables.sql
```

Also create the core tables manually (see README for full SQL) — `stores`, `owners`, `categories`, `products`, `inventory`, `customers`, `orders`, `order_items`.

After creating tables, insert a store row and set `telegram_chat_id` to your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot)) so the owner bot knows where to send reports.

---

## 4. Run locally

Start all backend services and bots with the unified launcher:

```bash
python main.py
```

This starts (in order, with 2-second delays):
- Owner Service — `http://localhost:8001`
- Customer Service — `http://localhost:8002`
- Agent Service — `http://localhost:8003`
- Owner Telegram Bot
- Customer Telegram Bot
- AI Scheduler (background)

Start the dashboard separately (in a new terminal):

```bash
cd owner-dashboard
npm run dev
```

Dashboard will be running at `http://localhost:3000`.

---

## 5. Configuring the Telegram bots

**Owner bot setup:**
1. Start a chat with your owner bot on Telegram.
2. Send `/start` — the bot registers your `telegram_chat_id`.
3. Update the `stores` table: `UPDATE stores SET telegram_chat_id = 'YOUR_CHAT_ID' WHERE id = 'YOUR_STORE_ID';`

**Customer bot deep link:**
The shareable customer link format is:
```
https://t.me/YOUR_CUSTOMER_BOT_USERNAME?start=YOUR_STORE_ID
```
Find your store ID in the Supabase `stores` table. The Settings page in the dashboard also displays this link.

---

## 6. Deploy to production

**Backend (Render):**

The `render.yaml` in the project root defines all five Render services (owner-service, customer-service, agent-service, customer-bot, owner-bot). Deploy with:

```bash
# Connect your GitHub repo to Render and apply the blueprint
# Or push to a connected repo — Render auto-deploys on push
```

Set the following secrets in the Render dashboard (marked `sync: false` in `render.yaml`):
- `SUPABASE_KEY`
- `OWNER_BOT_TOKEN`
- `CUSTOMER_BOT_TOKEN`
- `ANTHROPIC_API_KEY`

Update `OWNER_SERVICE_URL`, `CUSTOMER_SERVICE_URL`, and `AGENT_SERVICE_URL` in `.env` to point to the Render service URLs after first deploy.

**Frontend (Vercel):**

```bash
cd owner-dashboard
vercel --prod
```

Set environment variables in the Vercel project dashboard, including `NEXT_PUBLIC_API_URL` pointing to the deployed Render owner-service URL.

---

## Known local-only limitations

- The AI scheduler fires at hardcoded times (10:00, 16:00, 21:00, 21:05). To test an agent immediately, use the dashboard's agent trigger button or call `POST /api/events/trigger-agent` on the agent-service directly.
- The owner bot must receive `/start` and save a `telegram_chat_id` before any scheduled reports can be delivered.
- Redis is optional for the in-process event bus but required for inter-agent goal coordination (`store_goal:{store_id}` keys). Start Redis locally with `redis-server` or set `REDIS_URL` to a managed Redis URL (e.g., Upstash free tier).

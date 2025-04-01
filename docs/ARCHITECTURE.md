# BazaarOps — Architecture

---

## 1. Stack

| Layer | Tech |
|---|---|
| Framework | Next.js 14 (App Router, TypeScript) |
| Styling | Tailwind CSS 3 · Lucide React |
| Backend | FastAPI · Python 3.13 · Uvicorn |
| Database | Supabase PostgreSQL (managed) |
| AI | Anthropic Claude API — claude-sonnet-4-5 |
| Messaging | Redis pub/sub (inter-agent message bus) |
| Bots | python-telegram-bot 22.6 |
| NLP | fuzzywuzzy · python-Levenshtein |
| Scheduling | schedule (Python) |
| Hosting | Render (backend + bots) · Vercel (dashboard) |

---

## 2. Components

```
BazaarOps/
  owner-dashboard/     Next.js 14 web UI — analytics, inventory, orders, customers
  owner-service/       FastAPI :8001 — owner auth, inventory, orders, analytics API
  customer-service/    FastAPI :8002 — customer registration, orders, profile
  agent-service/       FastAPI :8003 — event bus, AI agent triggers, BI scheduler
  telegram-bots/
    owner-bot/         Telegram bot + scheduler — AI reports delivered to owner
    customer-bot/      Telegram bot — NLP ordering interface for end customers
```

### owner-dashboard

Next.js App Router SPA authenticated against Supabase. Pages: dashboard (BI analytics), inventory, orders, customers, credit, settings. Fetches from `owner-service` via `NEXT_PUBLIC_API_URL`. Dashboard uses `Promise.allSettled` to load trends, forecasts, anomalies, and profitability in parallel — a partial failure only hides that card, it does not break the page.

### owner-service

FastAPI service on port 8001. Handles owner authentication (email + bcrypt password), inventory CRUD, order lifecycle (confirm → deliver), and exposes the analytics routes that proxy into the BI agent module. All Supabase calls use the service role key. On delivery, calls the Telegram bot API to notify the customer.

### customer-service

FastAPI service on port 8002. Manages customer registration (name, phone, address, Telegram chat ID), product browsing, and order submission. Decrements inventory on order creation. Exposes endpoints consumed by the customer Telegram bot over HTTP.

### agent-service

FastAPI service on port 8003. Owns the in-process `EventBus` (a dict of `event_type → [async handlers]`). Accepts `POST /api/events/trigger` from other services and dispatches to subscribed handlers. Also hosts the BI scheduler loop that runs nightly at 21:00 UTC. The `CoordinatorAgent` handles multi-agent conflict resolution: incoming `AgentMessage` objects are prioritised and the winning recommendation is published back to the `REORDER` or `NOTIFICATION` agent.

### owner-bot (Telegram)

Receives automated reports from the scheduler. Agents run via `schedule` library: inventory analysis at 10:00 and 16:00, daily business report at 21:00, credit risk assessment at 21:05. Each agent calls Claude, formats a Markdown Telegram message, and sends it to the owner's chat ID stored in the `stores` table.

### customer-bot (Telegram)

Deep-link entry (`/start STORE_ID`) handles multi-store onboarding. NLP layer (`ConversationalOrderParser`) uses fuzzywuzzy for product name matching and Claude for conversational disambiguation. Falls back to command mode (`order <product> <qty>`) if the Anthropic API key is absent.

---

## 3. Data Flow

```
[Customer Telegram] --/start STORE_ID--> [customer-bot]
    --> GET /customer/profile  → customer-service
    --> register if new (name, phone, address onboarding)
    --> browse products, "order Rice 2"
    --> NLP parser (fuzzy match + Claude clarification)
    --> POST /order  → customer-service
        → INSERT orders + order_items
        → UPDATE inventory (decrement)
        → emit order.created event → agent-service
            → OrderAgent: validates, may block on credit risk
    --> owner sees order in dashboard

[Scheduler: 10:00 & 16:00]
    --> intelligent_restocking_agent.py
        → SELECT inventory + 30-day order_items from Supabase
        → POST to Anthropic Claude with structured JSON
        → parse analysis → send Telegram message to owner
        → for each critical item: send InlineKeyboard with WhatsApp supplier link

[Owner Dashboard] --> GET /api/owner/analytics/trends/{store_id}
    --> owner-service/routers/analytics.py
        → imports bi_agent module from agent-service/
        → calculate_trends(), detect_anomalies(), forecast_revenue()
        → return structured JSON
    --> dashboard renders bar charts and metric cards
```

1. Customer opens deep link → bot greets, checks `customers` table for existing profile.
2. New customer completes onboarding (name, phone, address) stored in Supabase.
3. Customer sends natural-language order → NLP parser matches product → confirmation step → `customer-service` creates order and decrements inventory.
4. Owner sees confirmed order in the dashboard; marks as delivered → Telegram notification sent to customer's chat ID.
5. Scheduler fires AI agents at scheduled times → Claude analyses structured data → Telegram report pushed to owner.

---

## 4. Database Schema

- `stores` — `id, name, phone, address, telegram_chat_id` — one row per business; `telegram_chat_id` links to owner's bot session for report delivery
- `owners` — `id, store_id, name, email, password_hash, telegram_chat_id` — bcrypt-hashed credentials; references store
- `categories` — `id, store_id, name` — product groupings per store
- `products` — `id, store_id, category_id, name, unit, cost_price, supplier_name, supplier_whatsapp, sales_velocity` — supplier WhatsApp stored for one-tap reorder links
- `inventory` — `id, store_id, product_id, quantity, unit_price, reorder_threshold, reorder_quantity, last_restocked` — stock levels; `reorder_threshold` drives AI alert logic
- `customers` — `id, store_id, name, phone, address, telegram_chat_id, telegram_username` — `telegram_chat_id` enables bot notifications
- `orders` — `id, store_id, customer_id, total_amount, status, payment_status, notes` — `payment_status=unpaid` identifies credit accounts
- `order_items` — `id, order_id, product_id, product_name, quantity, unit_price, subtotal` — denormalised `product_name` preserves history
- `agent_decisions` — `id, from_agents[], decision_type, input_data, output_decision, goal_used, store_id, outcome, outcome_metrics` — coordinator log; enables 30-day strategy adjustment

**Indexes:** Hot paths are `orders(store_id, created_at)` for trend queries and `order_items(order_id)` for profitability rollups. Supabase auto-indexes primary keys and foreign keys.

---

## 5. AI / LLM Design

### Input

Structured JSON — never raw user text or diffs. The restocking agent sends `{product, current_stock, reorder_threshold, total_sold_30days, avg_daily_sales, supplier, cost_price, unit}` per SKU. The credit agent sends `{customer_name, amount_due, days_pending, order_date}` per unpaid order.

### System prompt strategy

Each agent prompt identifies the model as a specialist (inventory assistant, credit analyst, business intelligence reporter). Prompts explicitly request Telegram-formatted Markdown output with emojis, constrain length to stay within Telegram message limits, and ask for actionable recommendations only — not general commentary.

### Response schema

```jsonc
// Restocking agent — free-form Markdown text response
// Claude returns analysis as a formatted string, not JSON
// Critical items are identified from structured data pre-call,
// not extracted from the LLM response — reducing hallucination risk

// BI agent — generate_bi_report returns plain Markdown
{
  "report_text": "string"  // Telegram-formatted Markdown
}
```

### Validation

The restocking and credit agents use Claude for prose output only. Critical item detection (items below `reorder_threshold`) is done in Python before the LLM call — the LLM adds context and framing, not the decision logic itself. The BI agent's `generate_bi_report` wraps the Anthropic call in a `try/except` that returns `False` on failure without crashing the scheduler.

### Failure handling

Each scheduled agent is wrapped in an independent `try/except`. A failure in one agent (Claude timeout, API quota) logs the error and returns `False` — it does not cancel the other scheduled agents that run in the same session. The event bus catches per-handler exceptions individually so a failing handler does not block sibling handlers.

---

## 6. API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Owner login — returns JWT stored in cookie |
| `POST` | `/api/auth/logout` | Clears auth cookie |
| `GET` | `/api/owner/inventory/{store_id}` | Lists all inventory items with product info |
| `POST` | `/api/owner/inventory` | Adds or updates an inventory item |
| `GET` | `/api/owner/orders/{store_id}` | Lists orders with customer info |
| `POST` | `/api/owner/orders/{order_id}/deliver` | Marks order delivered, sends customer Telegram notification |
| `GET` | `/api/owner/analytics/trends/{store_id}` | Week-over-week sales, top/bottom products, insights |
| `GET` | `/api/owner/analytics/forecast/{store_id}` | 7-day revenue forecast, stockout predictions, churn forecast |
| `GET` | `/api/owner/analytics/anomalies/{store_id}` | Detected order/inventory anomalies |
| `GET` | `/api/owner/analytics/profitability/{store_id}` | Per-product margin analysis and recommendations |
| `POST` | `/api/events/trigger` | Publish a typed event to the agent event bus |
| `POST` | `/api/bi/run-report/{store_id}` | Manually trigger a BI report for a store |
| `POST` | `/api/events/trigger-agent` | Manually invoke inventory, credit, or daily-report agent |

---

## 7. Security

- **Secrets:** All API keys in env vars — `ANTHROPIC_API_KEY`, `SUPABASE_KEY`, `OWNER_BOT_TOKEN`, `CUSTOMER_BOT_TOKEN`. `.env` is gitignored. Production secrets set in Render dashboard (sync: false) and Vercel encrypted env vars.
- **Auth tokens:** Owner session managed via HTTP-only cookie set by Next.js API route after Supabase credential verification. `SUPABASE_KEY` (service role) is server-only — never exposed as `NEXT_PUBLIC_`.
- **API key exposure:** Anthropic API key accessed only in server-side Python processes. The `NEXT_PUBLIC_SUPABASE_KEY` exposed to the browser is the anon key with row-level security, not the service role key.
- **Input validation:** Order amounts and quantities cast to `float` with explicit error handling before DB writes. Customer identity verified by matching `telegram_chat_id` against the store's customer table.

---

## 8. Error Handling & Reliability

| Failure | Behaviour |
|---|---|
| Claude API down / timeout | `try/except` in each agent — returns `False`, logs error, scheduler continues with remaining jobs |
| Event handler crash | `EventBus.publish` catches per-handler exceptions individually — other subscribers still receive the event |
| Supabase write fails | Error logged; order/inventory operations surface HTTP 500 to caller — no silent data loss |
| Customer bot NLP unavailable | Falls back to command-mode parsing (`order <product> <quantity>`) — feature degrades gracefully |
| BI scheduler missed (process restart) | Next scheduled interval fires as normal; no catch-up mechanism — acknowledged v2 gap |

---

## 9. Deployment

1. Backend services (owner-service, customer-service, agent-service) and Telegram bots deploy to **Render** via `render.yaml` — each service has its own Render web service in the Singapore region.
2. Build command: `pip install -r requirements.txt` from repo root. Start command: `cd <service> && uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Owner bot and scheduler run as a single Render process: `cd telegram-bots/owner-bot && python scheduler.py`.
4. Owner dashboard deploys to **Vercel** — `next build` runs automatically on push; `NEXT_PUBLIC_API_URL` points to the Render owner-service URL.
5. Supabase schema applied manually via SQL editor during initial setup (migrations in `agent-service/migrations/`).

---

## 10. Explicit Scope Cuts

- **Real-time dashboard updates via WebSockets** — polling on page load is sufficient for v1; Supabase Realtime would add complexity without clear need at current scale.
- **Multi-owner per store** — single owner per store simplifies auth and notification routing for MVP.
- **Persistent scheduler state** — schedule library runs in-process; missed jobs on restart are not replayed. Deferred to v2 (Celery Beat or APScheduler with DB backend).
- **Jira/Linear integration for reorder workflows** — WhatsApp deep links are sufficient for supplier contact at this scale.

# BazaarOps — Product Requirements Document

**Status:** Final
**Owner:** Tanish Poddar
**One-liner:** AI-powered store management platform — Telegram bots, Claude AI agents, and a real-time owner dashboard for small retail businesses.

---

## 1. Problem

Small retail shop owners in India — kirana stores, wholesale suppliers, neighbourhood vendors — manage inventory in notebooks or memory, lose track of which customers owe money, and have no idea which products are actually profitable. They are too busy running the counter to review sales data, and they cannot justify the cost or complexity of enterprise retail software. There is no lightweight tool that meets them where they already are (Telegram/WhatsApp) and gives them AI-grade insights without requiring a data analyst.

---

## 2. Goals (v1 / MVP)

1. Owner can log in, add products with supplier details, and set reorder thresholds in under 10 minutes.
2. Customers can discover the store's Telegram bot via a shareable deep link and place their first order without any onboarding beyond providing their name, phone, and address.
3. Claude AI analyses inventory daily and pushes actionable restocking recommendations to the owner's Telegram — no manual trigger required.
4. Owner can view this week's revenue, top products, and profit margin per product in the dashboard without leaving the browser.
5. Credit risk assessment runs daily and surfaces customers with overdue unpaid orders along with suggested collection strategies.
6. All backend services and Telegram bots deployed with a working live URL accessible to anyone.

---

## 3. Non-Goals (explicit scope cuts)

- **Payment processing** — BazaarOps tracks payment status (paid / unpaid) but does not integrate a payment gateway; actual money movement happens outside the system.
- **Multi-owner per store** — a single owner account per store is sufficient for v1; team access and role management would require per-user permissions and audit trails.
- **Mobile app** — Telegram bots serve as the mobile interface; a native app adds distribution complexity with no advantage for the target user.
- **WhatsApp Business API integration** — WhatsApp deep links for supplier contact are one-tap shortcuts, not a two-way API integration; full WhatsApp messaging would require a BSP and paid access.
- **Inventory barcode scanning** — manual entry is sufficient for the product catalogue sizes typical of small retail; scanning hardware adds friction to setup.

---

## 4. Users

**Primary:** Small retail store owners (kirana, wholesale, neighbourhood vendors) who want AI-generated business insights delivered to Telegram without managing spreadsheets or enterprise software.

**Secondary:** Store customers who want to browse products and place orders through Telegram without installing a dedicated app.

---

## 5. User Stories

1. *As a store owner,* I want to share a single Telegram link with my customers so that they can register themselves and start ordering without my involvement.
2. *As a store owner,* I want Claude to tell me which products to restock — and give me a one-tap button to contact the supplier — so that I never run out of fast-moving inventory without notice.
3. *As a store owner,* I want a daily Telegram report summarising today's revenue, top products, and credit outstanding so that I can review my business performance without opening the dashboard.
4. *As a store owner,* I want to mark an order as delivered in the dashboard and have the customer automatically notified via Telegram so that I do not need to send a manual message.
5. *As a customer,* I want to type a natural-language order like "order Rice 2kg" and have the bot understand it, even if I spell the product name slightly wrong.
6. *As a store owner,* I want to see which customers have unpaid orders and how long they have been outstanding, with suggested approaches for collecting payment.
7. *As a store owner,* I want the dashboard to show me this week's revenue vs. last week's, and which products are unprofitable, so that I can make pricing decisions.

---

## 6. Functional Requirements

### 6.1 Auth

- Owner registers with email and password; password stored as bcrypt hash.
- Login returns a session cookie used by subsequent dashboard API calls.
- Owner bot links Telegram chat ID to the store record to enable report delivery.

### 6.2 Inventory Management

- Owner can create product categories and add products with name, unit, cost price, supplier name, and supplier WhatsApp number.
- Each product has an inventory record with current quantity, unit price, reorder threshold, and reorder quantity.
- Placing a customer order automatically decrements the corresponding inventory quantity.
- Dashboard flags items at or below reorder threshold.

### 6.3 Customer Ordering (Telegram)

- Customer bot supports deep-link onboarding: `/start STORE_ID` associates the customer with the correct store.
- Onboarding collects name, phone, and address in a guided conversation flow.
- NLP parser uses fuzzy string matching to identify products from natural-language messages; falls back to structured command mode if AI is unavailable.
- Customers can view their order history and edit their profile (name, phone, address).

### 6.4 Order Management

- Orders are created with status `confirmed` and `payment_status` of `paid` or `unpaid`.
- Owner marks an order as delivered in the dashboard; system sends Telegram notification to the customer.
- Dashboard lists all orders with customer name, total, status, and date.

### 6.5 AI Agents

- Restocking agent runs at 10:00 and 16:00 — fetches inventory + 30-day sales, calls Claude, sends formatted Telegram report with WhatsApp supplier links for critical items.
- Credit risk agent runs at 21:05 — fetches all unpaid orders, calls Claude, sends per-customer risk assessment and collection strategy to owner's Telegram.
- Daily report agent runs at 21:00 — sends comprehensive end-of-day business summary.
- BI agent exposes trend, forecast, anomaly, and profitability calculations to the dashboard analytics API.

### 6.6 Business Intelligence Dashboard

- Trends: week-over-week revenue comparison, top and bottom products by revenue.
- Forecast: 7-day revenue projection with confidence level; per-product stockout risk.
- Anomaly detection: flags unusual order patterns or inventory movements.
- Profitability: per-product revenue, profit, and margin percentage with low-margin alerts.

### 6.7 Multi-Agent Coordination

- CoordinatorAgent resolves conflicts between agent recommendations using a priority system.
- Owner can set a business goal (maximize_profit, increase_customers, reduce_risk, balanced) stored in Redis; coordinator aligns decisions with the active goal.
- All coordinator decisions are logged to `agent_decisions` table with outcome tracking for 30-day strategy adjustment.

---

## 7. Non-Functional Requirements

- **Latency:** Dashboard analytics load in parallel via `Promise.allSettled` — a single slow endpoint does not block the page. Claude agent calls are asynchronous and do not block the Telegram bot.
- **Security:** Service role Supabase key never exposed to the browser. Anthropic API key server-side only. All sensitive env vars gitignored and stored in Render/Vercel encrypted env vars.
- **Cost:** Claude called on a schedule (at most 3 times/day per store) and on explicit user triggers — never on every page load or every message. Structured JSON inputs keep token counts predictable.
- **Reliability:** Each scheduled AI agent is independently wrapped in `try/except` — a Claude API failure does not cancel other scheduled jobs. EventBus catches per-handler exceptions individually.
- **Accessibility:** Telegram bots work on any phone with Telegram installed — no app install, no browser required for customers. Dashboard is web-based and mobile-responsive.

---

## 8. Success Metrics

| Metric | Target |
|---|---|
| First order placed by a new customer | Within 5 minutes of receiving the deep link |
| AI report delivery reliability | All 3 scheduled reports sent without manual intervention on typical day |
| Dashboard load time | All four analytics cards populated within 5 seconds on first load |
| Credit coverage | Every unpaid order surfaced in nightly credit analysis |

---

## 9. Risks & Open Questions

- **Anthropic API rate limits** — free tier limits may throttle agents if many stores run simultaneously. Mitigated by on-demand and scheduled calls only, never per-message.
- **Telegram delivery reliability** — if the owner's `telegram_chat_id` is not stored in the `stores` table (e.g., never started the owner bot), reports silently fail. Mitigated by a setup check in the settings page.
- **Scheduler process restart** — if the Render owner-bot service restarts between 21:00 and 21:05, the nightly reports are missed with no catch-up. This is a known gap deferred to v2.
- **Open question:** Should the credit agent automatically send a payment reminder to the customer's Telegram, or only notify the owner? Currently owner-only; customer-facing reminders require consent design.

---

## 10. v2 Candidates

- **Persistent job scheduler** — Celery + Beat (or APScheduler with DB backend) so scheduled reports survive process restarts.
- **Customer-facing payment reminders** — opt-in Telegram messages to customers with overdue balances.
- **Multi-owner / staff accounts** — role-based access for shop assistants who can update inventory but not view financial reports.
- **WhatsApp Business API** — replace deep links with a full two-way supplier ordering channel.
- **Inventory barcode scanning** — mobile camera integration for faster stock entry.
- **GitHub Check Runs style order gates** — block delivery confirmation if credit risk score exceeds threshold, with owner override.

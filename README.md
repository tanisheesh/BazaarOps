<p align="center">
  <img src="owner-dashboard/app/favicon.ico" width="64" height="64" alt="BazaarOps logo">
</p>

<h1 align="center">BazaarOps</h1>

<p align="center">
  <strong>AI-powered store management platform — Telegram bots, Claude AI agents, and a real-time owner dashboard for small retail businesses.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-black?style=flat-square&logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Claude_API-D97757?style=flat-square" alt="Claude API">
  <img src="https://img.shields.io/badge/Telegram-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram">
  <img src="https://img.shields.io/badge/license-GPL--3.0-F97316?style=flat-square" alt="License">
</p>

---

## What is BazaarOps?

Small retail shop owners in India track inventory in notebooks, lose money to uncollected credit, and have no visibility into which products are actually driving profit. BazaarOps replaces that with a multi-agent AI system: Claude analyzes sales velocity and credit patterns daily, then pushes actionable alerts directly to the owner's Telegram. Customers place orders through a conversational Telegram bot with NLP — no app to install, no signup friction.

---

## What you get

- **Conversational customer ordering** — Customers browse and order via Telegram using natural language (`order Rice 2kg`); fuzzy matching handles typos and shorthand product names.
- **Claude AI inventory analysis** — Twice-daily analysis of stock levels vs. sales velocity, with one-tap WhatsApp links to contact suppliers for critical items.
- **Credit risk assessment** — Daily Claude-powered analysis of unpaid orders, with tailored collection strategies per customer risk profile.
- **Business intelligence dashboard** — Week-over-week trends, 7-day revenue forecasts, stockout predictions, profitability by product, and anomaly alerts in a Next.js UI.
- **Multi-agent event bus** — Coordinator agent resolves conflicts between inventory, credit, churn, and order agents using Redis pub/sub; decisions are logged and outcomes tracked for strategy adjustment.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind CSS · Lucide React |
| Backend | FastAPI · Python 3.13 · Uvicorn |
| Database | Supabase PostgreSQL |
| AI | Anthropic Claude API (claude-sonnet-4-5) |
| Messaging | Redis pub/sub (inter-agent message bus) |
| Bots | python-telegram-bot 22.6 |
| NLP | fuzzywuzzy · python-Levenshtein |
| Scheduling | schedule (Python) |
| Hosting | Render (backend services + bots) · Vercel (dashboard) |

---

## Engineering Decisions

**Why a multi-agent event bus over direct API calls between services?**
Agents emit typed events (INVENTORY_LOW, CREDIT_RISK_HIGH, CUSTOMER_CHURN_RISK) that any subscriber can act on independently. A new agent can be added without touching existing code — the coordinator handles conflict resolution without tight coupling.

**Why Claude for inventory and credit analysis rather than rule-based alerts?**
Reorder thresholds are too blunt — a product below threshold but with zero recent sales should not trigger the same alert as one selling 10 units/day. Claude receives structured JSON of sales velocity and stock data, not raw data dumps, and produces context-aware recommendations the owner can act on immediately.

**Why Telegram instead of a dedicated mobile app for customers?**
Zero install friction. The primary customer segment is neighbourhood shop regulars who already use WhatsApp/Telegram. Deep linking (`t.me/BazaarOpsCustomerHelpBot?start=STORE_ID`) lets owners share a single link that onboards customers to the correct store automatically.

**What would you do differently in v2?**
The scheduler runs inside the bot process — if the bot restarts, a scheduled report can be skipped silently. Moving scheduled jobs to a proper task queue (Celery + Beat, or APScheduler with a persistent store) would make the scheduling layer independently restartable and observable.

---

## Docs

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product requirements — goals, user stories, non-goals |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, component breakdown |
| [Decisions](docs/DECISIONS.md) | Every major technical decision and why |
| [Setup](docs/SETUP.md) | Local dev setup, env vars, deployment |

---

## Author

**Tanish Poddar** — [tanisheesh.in](https://tanisheesh.in) · [LinkedIn](https://linkedin.com/in/tanisheesh) · [GitHub](https://github.com/tanisheesh)

# Engineering Decisions — BazaarOps

---

## Decision 1 — Event bus with typed agent messages over direct inter-service HTTP calls

**Context:** Multiple agents (inventory, credit, order, customer lifecycle) need to react to the same business events (order created, stock low, payment overdue). The alternatives were: (a) each service calls the others directly, or (b) a shared event bus where agents subscribe to typed events.

**Decision:** Async in-process `EventBus` backed by Redis pub/sub for inter-agent messages; agents communicate via typed `AgentMessage` objects with priority and correlation IDs.

**Reason:** Direct HTTP calls create tight coupling — adding a new agent requires modifying every service it depends on. The event bus lets a new subscriber be wired up in one place without touching the emitter. Redis pub/sub provides persistence across process boundaries without the overhead of a full message broker like RabbitMQ, which would be over-engineered for current scale.

**Tradeoff:** The in-process `EventBus` instance is not shared across Render service instances — horizontal scaling would require moving entirely to Redis Streams or a managed queue. At v1 scale (one instance per service) this is acceptable.

---

## Decision 2 — Claude for prose analysis only; structured data decisions stay in Python

**Context:** The restocking agent needed to decide which products to alert on and what to recommend. Options: let Claude make the full decision from raw DB rows, or compute the critical items in Python and use Claude only for the human-readable explanation.

**Decision:** Python computes which items are below `reorder_threshold` and calculates 30-day sales velocity before calling Claude. Claude receives a pre-filtered structured JSON and is asked to write the analysis, not to identify which items are critical.

**Reason:** Keeping the decision logic in Python makes it auditable and deterministic — the owner can trust that every item flagged as critical is genuinely below threshold, not an LLM inference. It also keeps token counts low (Claude only sees relevant items, not the full catalogue) and avoids hallucination on numerical thresholds. The same pattern applies to credit risk: Python identifies unpaid orders and computes `days_pending`; Claude writes the collection strategy.

**Tradeoff:** The split adds a pre-processing layer in Python that must be maintained as the schema evolves. If the analysis logic grows complex, keeping Python and Claude in sync becomes a maintenance cost.

---

## Decision 3 — Telegram as the customer interface instead of a web app or native app

**Context:** Customers needed a way to browse products and place orders. Options: (a) a customer-facing web/mobile app, (b) WhatsApp Business API, (c) Telegram bot with deep linking.

**Decision:** Telegram bot with store-specific deep links (`t.me/BazaarOpsCustomerHelpBot?start=STORE_ID`).

**Reason:** The target customer demographic already uses Telegram or WhatsApp daily. A Telegram bot requires zero app install, works on any smartphone, and the deep link handles multi-store onboarding automatically — the owner shares one link, and all customers are registered to the correct store. WhatsApp Business API requires a paid BSP relationship and approval process; Telegram has no such gating.

**Tradeoff:** Customers who do not use Telegram are excluded. Telegram's UX constraints (keyboard menus, inline buttons) limit the ordering flow compared to a native app — there is no product image grid or cart review screen.

---

## Decision 4 — schedule library for AI job scheduling instead of a task queue

**Context:** Three AI jobs needed to run at fixed times each day (10:00, 16:00, 21:00, 21:05). Options: Celery + Beat, APScheduler, or the Python `schedule` library running in the bot process.

**Decision:** `schedule` library running as a background loop inside the owner-bot process (`scheduler.py`).

**Reason:** Zero infrastructure overhead — no Celery worker, no Beat process, no broker. The entire scheduler is a 30-line Python file that is easy to read and modify. For a single-store MVP with fixed daily cadence, the simplicity advantage outweighed the reliability difference.

**Tradeoff:** If the owner-bot process restarts between job fire times (e.g., Render cold start), the job is silently missed — no retry, no dead-letter, no alerting. The `schedule` library has no persistence or missed-job detection. This is the most significant reliability gap in v1 and is explicitly called out in the PRD as a v2 fix.

---

## Decision 5 — Supabase over a self-hosted Postgres instance

**Context:** The project needed a relational database with auth, real-time capability, and minimal ops overhead. Options: Neon (serverless Postgres), Railway Postgres, self-hosted Postgres on Render, or Supabase.

**Decision:** Supabase managed PostgreSQL.

**Reason:** Supabase provides a hosted Postgres instance, a JavaScript and Python client library, row-level security primitives, and a built-in SQL editor — all on a free tier suitable for a portfolio project. The service role key / anon key split maps cleanly onto the server/client security model (service role on backend only, anon key for the Next.js frontend with RLS). The SQL migrations in `agent-service/migrations/` were run via the Supabase SQL editor during initial setup.

**Tradeoff:** The application is tightly coupled to Supabase's client library and connection model. Migrating to a different Postgres host would require replacing the `supabase` Python client with `asyncpg` or `psycopg2` throughout all three services.

---

## What I'd do differently in v2

- **Persistent job scheduler** — Replace the `schedule` library with Celery Beat (or APScheduler backed by the Supabase DB) so missed jobs are logged and retried after a process restart. The current setup silently drops reports on service restart.
- **Structured LLM output with Zod/Pydantic validation** — Currently Claude returns free-form Markdown for all agents. Adding a JSON response mode with schema validation would make the output machine-readable (e.g., parseable reorder quantities for automatic PO generation) and catch malformed responses before they reach the owner.
- **Row-level security enforcement** — Supabase RLS policies are defined in the schema but the backend uses the service role key (which bypasses RLS). Switching to a per-store JWT and the anon key on the backend would enforce data isolation at the DB layer rather than relying on application-level `WHERE store_id = X` filters.

---

## Explicit non-decisions (deferred to v2)

| Feature | Why deferred |
|---|---|
| Payment gateway integration | Tracking paid/unpaid status is sufficient for v1; actual payment processing introduces regulatory and banking complexity out of scope for a portfolio MVP |
| Customer-facing Telegram payment reminders | Requires opt-in design and consent management; owner-only notifications are simpler and sufficient to validate the credit risk use case |
| Horizontal scaling / multi-instance event bus | Single Render instance per service is sufficient at current scale; Redis Streams would be needed if traffic warranted multiple instances |
| Barcode scanning for inventory entry | Manual product entry is fast enough for the catalogue sizes typical of small retail; scanning hardware adds setup friction with no benefit at MVP scale |

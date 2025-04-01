# Agent Service – Database Migrations

## Running migrations against Supabase

### Option 1: Supabase SQL Editor (recommended for one-off runs)

1. Open your Supabase project dashboard.
2. Navigate to **SQL Editor** in the left sidebar.
3. Paste the contents of the migration file (e.g. `001_order_triggers.sql`).
4. Click **Run**.

All migration files are idempotent — `CREATE OR REPLACE FUNCTION` and
`DROP TRIGGER IF EXISTS` ensure they can be re-run safely without errors.

### Option 2: Supabase CLI

```bash
# Install the CLI if you haven't already
npm install -g supabase

# Link to your project (run once)
supabase link --project-ref <your-project-ref>

# Push a specific migration
supabase db push --file agent-service/migrations/001_order_triggers.sql
```

### Option 3: psql directly

```bash
psql "$DATABASE_URL" -f agent-service/migrations/001_order_triggers.sql
```

`DATABASE_URL` is the connection string from your Supabase project settings
(**Settings → Database → Connection string → URI**).

---

## How pg_notify works and why we use it

PostgreSQL's `pg_notify(channel, payload)` is a lightweight, built-in
publish/subscribe mechanism that runs inside the database transaction.
When a row is inserted or updated in the `orders` table, the trigger
function fires synchronously and calls `pg_notify('order_events', <json>)`.
Any client that is `LISTEN`-ing on the `order_events` channel receives the
notification immediately — with no polling and no external message broker
required at the database layer.

**Why pg_notify instead of application-level publishing?**

- **Atomicity** – the notification is sent only if the transaction commits,
  so there is no risk of publishing an event for a write that was rolled back.
- **Zero extra infrastructure** – no Kafka, no RabbitMQ, no extra service
  needed between the database and the agent.
- **Low latency** – notifications are delivered in milliseconds after commit.
- **Simplicity** – a single SQL function handles all order event types.

---

## How the agent-service listens to these notifications

The agent-service uses the `psycopg2` (or `asyncpg`) PostgreSQL driver to
open a persistent connection and issue a `LISTEN order_events` command.
When a notification arrives, the service:

1. Parses the JSON payload from the notification.
2. Maps `event_type` to the corresponding `EventType` enum value.
3. Constructs a canonical `Event` object (see `events/event_types.py`).
4. Publishes the event to the Redis pub/sub channel so that all registered
   `EventSubscriber` handlers (see `events/subscriber.py`) can process it.

This two-step bridge (PostgreSQL → agent-service → Redis) keeps the database
decoupled from the downstream agent logic while still guaranteeing that every
committed order change produces an event.

### Payload schema

Each notification payload is a JSON object with the following fields:

| Field          | Type   | Description                                      |
|----------------|--------|--------------------------------------------------|
| `event_type`   | string | `order.created`, `order.updated`, `order.completed` |
| `order_id`     | uuid   | Primary key of the affected order row            |
| `customer_id`  | uuid   | Customer who placed the order                    |
| `store_id`     | uuid   | Store the order belongs to                       |
| `total_amount` | number | Order total in the store's currency              |
| `status`       | string | Current order status (e.g. `confirmed`, `completed`) |
| `timestamp`    | string | UTC ISO 8601 timestamp of when the trigger fired |

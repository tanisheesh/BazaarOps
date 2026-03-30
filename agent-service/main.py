from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory
root_dir = Path(__file__).parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from events.event_bus import Event, event_bus
from agents.order_agent import OrderAgent
from agents.summary_agent import SummaryAgent
import asyncio
from datetime import datetime, timezone

app = FastAPI(
    title="BazaarOps Agent Service",
    description="AI Agents with Claude SDK",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
print("🤖 Initializing agents...")
order_agent = OrderAgent()
summary_agent = SummaryAgent()
print("✅ All agents ready!")

@app.get("/")
async def root():
    return {
        "service": "agent-service",
        "status": "running",
        "sdk": "claude-agent-sdk",
        "agents": ["order_agent", "summary_agent"]
    }

def _do_trigger(event_type: str, store_id: str, payload: dict, background_tasks: BackgroundTasks):
    """Shared logic for triggering an event"""
    event = Event(
        type=event_type,
        store_id=store_id,
        payload=payload or {}
    )
    background_tasks.add_task(event_bus.publish, event)
    return {
        "success": True,
        "event_type": event_type,
        "message": "Event triggered"
    }

@app.post("/api/events/trigger")
async def trigger_event_post(
    event_type: str,
    store_id: str,
    payload: dict = None,
    background_tasks: BackgroundTasks = None,
):
    """Trigger an event (POST)"""
    return _do_trigger(event_type, store_id, payload or {}, background_tasks)

@app.get("/api/events/trigger")
async def trigger_event_get(
    event_type: str,
    store_id: str,
    payload: str = "{}",
    background_tasks: BackgroundTasks = None,
):
    """Trigger an event (GET, for browser/testing)"""
    import json
    try:
        payload_dict = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        payload_dict = {}
    return _do_trigger(event_type, store_id, payload_dict, background_tasks)

@app.get("/health")
async def health():
    return {"status": "healthy", "sdk": "claude-agent-sdk"}


# ---------------------------------------------------------------------------
# 6.7 Scheduler job for daily BI report at 9 PM
# ---------------------------------------------------------------------------

async def _run_daily_bi_reports():
    """Run BI reports for all active stores. Called by scheduler at 9 PM."""
    from supabase import create_client
    from agents.bi_agent import generate_bi_report

    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
    )
    try:
        stores = supabase.table("stores").select("id").execute()
        store_ids = [s["id"] for s in (stores.data or [])]
    except Exception as exc:
        print(f"❌ BI scheduler: could not fetch stores: {exc}")
        return

    for store_id in store_ids:
        try:
            await generate_bi_report(store_id)
            print(f"✅ BI report sent for store {store_id}")
        except Exception as exc:
            print(f"❌ BI report failed for store {store_id}: {exc}")


async def _bi_scheduler_loop():
    """Background loop that fires daily BI reports at 21:00 local time."""
    while True:
        now = datetime.now(timezone.utc)
        # Target: 21:00 UTC (9 PM)
        target_hour = 21
        seconds_until = ((target_hour - now.hour) % 24) * 3600 - now.minute * 60 - now.second
        if seconds_until <= 0:
            seconds_until += 86400
        print(f"⏰ BI scheduler: next run in {seconds_until // 3600}h {(seconds_until % 3600) // 60}m")
        await asyncio.sleep(seconds_until)
        print("📊 Running daily BI reports...")
        await _run_daily_bi_reports()


@app.on_event("startup")
async def start_bi_scheduler():
    """Start the BI report scheduler on app startup."""
    asyncio.create_task(_bi_scheduler_loop())
    print("⏰ BI report scheduler started (daily at 9 PM UTC)")


@app.post("/api/bi/run-report/{store_id}")
async def trigger_bi_report(store_id: str):
    """Manually trigger a BI report for a store."""
    from agents.bi_agent import generate_bi_report
    success = await generate_bi_report(store_id)
    return {"success": success, "store_id": store_id}

@app.post("/api/events/trigger-agent")
async def trigger_agent_manual(request: dict):
    """
    Manually trigger AI agents
    """
    store_id = request.get("store_id")
    agent_type = request.get("agent_type")
    
    print(f"🤖 Manual trigger: {agent_type} for store {store_id}")
    
    try:
        # Import from telegram-bots/owner-bot/agents using importlib
        import importlib.util
        import sys
        
        owner_bot_agents = Path(__file__).parent.parent / "telegram-bots" / "owner-bot" / "agents"
        
        if agent_type == "inventory":
            spec = importlib.util.spec_from_file_location(
                "intelligent_restocking_agent",
                owner_bot_agents / "intelligent_restocking_agent.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            await module.analyze_inventory_with_ai(store_id)
            return {"success": True, "message": "Inventory analysis sent"}
            
        elif agent_type == "credit":
            spec = importlib.util.spec_from_file_location(
                "intelligent_credit_agent",
                owner_bot_agents / "intelligent_credit_agent.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            await module.analyze_credit_with_ai(store_id)
            return {"success": True, "message": "Credit analysis sent"}
            
        elif agent_type == "daily_report":
            spec = importlib.util.spec_from_file_location(
                "daily_report_agent",
                owner_bot_agents / "daily_report_agent.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            await module.generate_daily_report(store_id)
            return {"success": True, "message": "Daily report sent"}
            
        else:
            return {"success": False, "message": "Unknown agent type"}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
from dotenv import load_dotenv

# Load .env first so agents get SUPABASE_* etc.
load_dotenv()

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from events.event_bus import Event, event_bus
from agents.order_agent import OrderAgent
from agents.summary_agent import SummaryAgent

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
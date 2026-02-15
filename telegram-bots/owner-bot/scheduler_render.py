"""
Owner Bot + Scheduler with HTTP Server for Render Free Tier
Runs bot + scheduler + dummy HTTP server on PORT
"""
import os
import asyncio
from threading import Thread
from flask import Flask
import schedule
import time
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load .env
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Import AI agents
import sys
sys.path.append(os.path.dirname(__file__))
from agents.daily_report_agent import generate_daily_report
from agents.intelligent_restocking_agent import analyze_inventory_with_ai
from agents.intelligent_credit_agent import analyze_credit_with_ai

# Get PORT from Render
PORT = int(os.getenv("PORT", 8080))

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "running", "service": "owner-bot-scheduler"}

@app.route('/health')
def health():
    return {"status": "healthy"}

def get_all_stores():
    """Get all active stores"""
    try:
        stores = supabase.table("stores").select("id, telegram_chat_id, name").execute()
        return [s for s in stores.data if s.get('telegram_chat_id')]
    except Exception as e:
        print(f"Error fetching stores: {e}")
        return []

async def run_daily_reports():
    """Run daily reports for all stores"""
    print(f"[{datetime.now()}] 🌙 Running end-of-day reports...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await generate_daily_report(store['id'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error: {e}")

async def run_ai_inventory_analysis():
    """Run AI inventory analysis"""
    print(f"[{datetime.now()}] 🤖 Running AI Inventory Analysis...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await analyze_inventory_with_ai(store['id'])
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Error: {e}")

async def run_ai_credit_analysis():
    """Run AI credit analysis"""
    print(f"[{datetime.now()}] 💳 Running AI Credit Analysis...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await analyze_credit_with_ai(store['id'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error: {e}")

def schedule_jobs():
    """Schedule all AI agent jobs"""
    schedule.every().day.at("10:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    schedule.every().day.at("16:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    schedule.every().day.at("21:00").do(lambda: asyncio.run(run_daily_reports()))
    schedule.every().day.at("21:05").do(lambda: asyncio.run(run_ai_credit_analysis()))
    
    print("✅ AI Agent Scheduler started!")
    print("🤖 AI Inventory Analysis: 10:00 AM, 4:00 PM")
    print("🌙 End-of-Day Reports: 9:00 PM")
    print("💳 AI Credit Analysis: 9:05 PM")

def run_flask():
    """Run Flask in background"""
    app.run(host='0.0.0.0', port=PORT)

def run_scheduler():
    """Run scheduler"""
    schedule_jobs()
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_bot():
    """Run owner bot"""
    from bot import main as run_owner_bot
    run_owner_bot()

if __name__ == "__main__":
    print(f"🚀 Starting Owner Bot + Scheduler on port {PORT}")
    
    # Start Flask in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"✅ HTTP server running on port {PORT}")
    
    # Start scheduler in background
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✅ Scheduler running")
    
    # Run bot in main thread
    print("🤖 Starting Telegram bot...")
    run_bot()

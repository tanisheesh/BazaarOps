"""
Agent Scheduler - Runs AI-powered agents at scheduled times
"""
import os
import asyncio
import schedule
import time
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load .env from root directory
root_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Import AI agents
import sys
sys.path.append(os.path.dirname(__file__))
from agents.daily_report_agent import generate_daily_report
from agents.intelligent_restocking_agent import analyze_inventory_with_ai
from agents.intelligent_credit_agent import analyze_credit_with_ai

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_all_stores():
    """Get all active stores"""
    try:
        stores = supabase.table("stores").select("id, telegram_chat_id, name").execute()
        return [s for s in stores.data if s.get('telegram_chat_id')]
    except Exception as e:
        print(f"Error fetching stores: {e}")
        return []


async def run_daily_reports():
    """Run daily reports for all stores at closing time"""
    print(f"[{datetime.now()}] 🌙 Running end-of-day reports...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await generate_daily_report(store['id'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error running daily report for {store['name']}: {e}")


async def run_ai_inventory_analysis():
    """Run AI-powered inventory analysis"""
    print(f"[{datetime.now()}] 🤖 Running AI Inventory Analysis...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await analyze_inventory_with_ai(store['id'])
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Error running AI analysis for {store['name']}: {e}")


async def run_ai_credit_analysis():
    """Run AI-powered credit analysis at closing time"""
    print(f"[{datetime.now()}] 💳 Running AI Credit Analysis...")
    stores = get_all_stores()
    
    for store in stores:
        try:
            await analyze_credit_with_ai(store['id'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error running AI credit analysis for {store['name']}: {e}")


def schedule_jobs():
    """Schedule all AI agent jobs"""
    
    # AI Inventory Analysis - Twice daily (10 AM, 4 PM)
    schedule.every().day.at("10:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    schedule.every().day.at("16:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    
    # Daily report at closing time (9 PM)
    schedule.every().day.at("21:00").do(lambda: asyncio.run(run_daily_reports()))
    
    # AI Credit analysis at closing time (9:05 PM)
    schedule.every().day.at("21:05").do(lambda: asyncio.run(run_ai_credit_analysis()))
    
    print("✅ AI Agent Scheduler started!")
    print("🤖 AI Inventory Analysis: 10:00 AM, 4:00 PM")
    print("🌙 End-of-Day Reports: 9:00 PM")
    print("💳 AI Credit Analysis: 9:05 PM")


if __name__ == "__main__":
    schedule_jobs()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)

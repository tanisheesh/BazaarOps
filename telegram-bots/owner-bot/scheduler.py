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
from agents.customer_lifecycle_agent import (
    send_birthday_wishes,
    run_re_engagement,
)

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


async def run_birthday_wishes():
    """Send birthday wishes to customers at 9 AM"""
    print(f"[{datetime.now()}] 🎂 Running Birthday Wishes...")
    stores = get_all_stores()

    for store in stores:
        try:
            await send_birthday_wishes(store['id'])
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error sending birthday wishes for {store['name']}: {e}")


async def run_vip_detection():
    """Run VIP detection for all stores"""
    print(f"[{datetime.now()}] ⭐ Running VIP Detection...")
    import sys as _sys
    import os as _os
    agent_service_path = _os.path.join(
        _os.path.dirname(__file__), "..", "..", "agent-service"
    )
    _sys.path.insert(0, agent_service_path)
    try:
        from agents.customer_lifecycle_agent import VIPDetector
        detector = VIPDetector()
        stores = get_all_stores()
        for store in stores:
            try:
                result = detector.update_vip_flags(store['id'])
                print(f"VIP update for {store['name']}: {result}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error running VIP detection for {store['name']}: {e}")
    except ImportError as e:
        print(f"⚠️ Could not import VIPDetector: {e}")


async def run_churn_prediction():
    """Run churn prediction for all stores"""
    print(f"[{datetime.now()}] 📉 Running Churn Prediction...")
    import sys as _sys
    import os as _os
    agent_service_path = _os.path.join(
        _os.path.dirname(__file__), "..", "..", "agent-service"
    )
    _sys.path.insert(0, agent_service_path)
    try:
        from agents.customer_lifecycle_agent import ChurnPredictor
        predictor = ChurnPredictor()
        stores = get_all_stores()
        for store in stores:
            try:
                result = predictor.update_churn_risk(store['id'])
                print(f"Churn update for {store['name']}: {result}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error running churn prediction for {store['name']}: {e}")
    except ImportError as e:
        print(f"⚠️ Could not import ChurnPredictor: {e}")


async def run_re_engagement_jobs():
    """Run re-engagement messages for at-risk customers"""
    print(f"[{datetime.now()}] 📨 Running Re-engagement Jobs...")
    stores = get_all_stores()

    for store in stores:
        try:
            await run_re_engagement(store['id'])
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error running re-engagement for {store['name']}: {e}")


def schedule_jobs():
    """Schedule all AI agent jobs"""
    
    # AI Inventory Analysis - Twice daily (10 AM, 4 PM)
    schedule.every().day.at("10:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    schedule.every().day.at("16:00").do(lambda: asyncio.run(run_ai_inventory_analysis()))
    
    # Daily report at closing time (9 PM)
    schedule.every().day.at("21:00").do(lambda: asyncio.run(run_daily_reports()))
    
    # AI Credit analysis at closing time (9:05 PM)
    schedule.every().day.at("21:05").do(lambda: asyncio.run(run_ai_credit_analysis()))

    # 3.3.1 Birthday wishes at 9 AM daily
    schedule.every().day.at("09:00").do(lambda: asyncio.run(run_birthday_wishes()))

    # 3.7 VIP detection - daily at 2 AM (low traffic)
    schedule.every().day.at("02:00").do(lambda: asyncio.run(run_vip_detection()))

    # 3.7 Churn prediction - daily at 2:05 AM
    schedule.every().day.at("02:05").do(lambda: asyncio.run(run_churn_prediction()))

    # 3.5.3 Re-engagement messages - daily at 10 AM
    schedule.every().day.at("10:00").do(lambda: asyncio.run(run_re_engagement_jobs()))
    
    print("✅ AI Agent Scheduler started!")
    print("🤖 AI Inventory Analysis: 10:00 AM, 4:00 PM")
    print("🌙 End-of-Day Reports: 9:00 PM")
    print("💳 AI Credit Analysis: 9:05 PM")
    print("🎂 Birthday Wishes: 9:00 AM")
    print("⭐ VIP Detection: 2:00 AM")
    print("📉 Churn Prediction: 2:05 AM")
    print("📨 Re-engagement Messages: 10:00 AM")


if __name__ == "__main__":
    schedule_jobs()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)

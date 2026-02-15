"""
BazaarOps - Single Entry Point with Claude AI Agents
Runs everything using subprocess for proper isolation
"""
import subprocess
import sys
import time
from pathlib import Path

# Get base directory
BASE_DIR = Path(__file__).parent.absolute()

def main():
    print("=" * 70)
    print("🛒 BazaarOps - AI-Powered Store Management System")
    print("=" * 70)
    print("\n🧠 Powered by Claude 3.5 Sonnet AI Agents\n")
    print("Starting all services...\n")
    
    processes = []
    
    try:
        # 1. Start FastAPI Backend
        print("🚀 Starting FastAPI Backend...")
        fastapi_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR / "owner-service"),
            shell=True
        )
        processes.append(("FastAPI-Backend", fastapi_process))
        print("✅ Started: FastAPI-Backend (Port 8001)")
        time.sleep(2)
        
        # 2. Start Next.js Dashboard
        print("🎨 Starting Next.js Dashboard...")
        nextjs_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(BASE_DIR / "owner-dashboard"),
            shell=True
        )
        processes.append(("NextJS-Dashboard", nextjs_process))
        print("✅ Started: NextJS-Dashboard (Port 3000)")
        time.sleep(2)
        
        # 3. Start Telegram Bot
        print("🤖 Starting Telegram Bot...")
        bot_process = subprocess.Popen(
            [sys.executable, "bot.py"],
            cwd=str(BASE_DIR / "telegram-bots" / "owner-bot"),
            shell=True
        )
        processes.append(("Telegram-Bot", bot_process))
        print("✅ Started: Telegram-Bot")
        time.sleep(2)
        
        # 4. Start AI Scheduler
        print("🧠 Starting AI Agent Scheduler...")
        scheduler_process = subprocess.Popen(
            [sys.executable, "scheduler.py"],
            cwd=str(BASE_DIR / "telegram-bots" / "owner-bot"),
            shell=True
        )
        processes.append(("Claude-AI-Scheduler", scheduler_process))
        print("✅ Started: Claude-AI-Scheduler")
        
        print("\n" + "=" * 70)
        print("🎉 All Services Running Successfully!")
        print("=" * 70)
        print("\n📱 Access Points:")
        print("   • Dashboard: http://localhost:3000")
        print("   • API: http://localhost:8001")
        print("   • Bot: @BazaarOpsAdminBot")
        print("\n🧠 Claude AI Agents (Automated):")
        print("   • 10:00 AM - AI Inventory Analysis (demand prediction, restocking)")
        print("   • 04:00 PM - AI Inventory Analysis (afternoon check)")
        print("   • 09:00 PM - AI Daily Business Insights (performance analysis)")
        print("   • 09:05 PM - AI Credit Risk Assessment (collection strategies)")
        print("\n💡 Features:")
        print("   • Real-time inventory management")
        print("   • Intelligent restocking recommendations")
        print("   • Credit risk analysis with collection strategies")
        print("   • Daily AI-powered business insights")
        print("   • WhatsApp supplier integration")
        print("   • Telegram notifications")
        print("\nPress Ctrl+C to stop all services\n")
        
        # Keep running and monitor processes
        while True:
            time.sleep(5)
            # Check if any process died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ {name} stopped unexpectedly!")
            
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down all services...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
        
        # Wait for all to terminate
        time.sleep(2)
        for name, proc in processes:
            if proc.poll() is None:
                proc.kill()
        
        print("Goodbye!")

if __name__ == "__main__":
    main()

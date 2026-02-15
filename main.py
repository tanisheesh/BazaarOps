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
        # 1. Start Owner Service (FastAPI Backend)
        print("🚀 Starting Owner Service...")
        owner_service_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR / "owner-service"),
            shell=True
        )
        processes.append(("Owner-Service", owner_service_process))
        print("✅ Started: Owner-Service (Port 8001)")
        time.sleep(2)
        
        # 2. Start Customer Service (FastAPI Backend)
        print("🛍️ Starting Customer Service...")
        customer_service_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR / "customer-service"),
            shell=True
        )
        processes.append(("Customer-Service", customer_service_process))
        print("✅ Started: Customer-Service (Port 8002)")
        time.sleep(2)
        
        # 3. Start Agent Service (AI Agents)
        print("🤖 Starting Agent Service...")
        agent_service_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(BASE_DIR / "agent-service"),
            shell=True
        )
        processes.append(("Agent-Service", agent_service_process))
        print("✅ Started: Agent-Service (Port 8003)")
        time.sleep(2)
        
        # 4. Start Owner Telegram Bot
        print("📱 Starting Owner Bot...")
        owner_bot_process = subprocess.Popen(
            [sys.executable, "bot.py"],
            cwd=str(BASE_DIR / "telegram-bots" / "owner-bot"),
            shell=True
        )
        processes.append(("Owner-Bot", owner_bot_process))
        print("✅ Started: Owner-Bot (@BazaarOpsAdminBot)")
        time.sleep(2)
        
        # 5. Start Customer Telegram Bot
        print("🛒 Starting Customer Bot...")
        customer_bot_process = subprocess.Popen(
            [sys.executable, "bot.py"],
            cwd=str(BASE_DIR / "telegram-bots" / "customer-bot"),
            shell=True
        )
        processes.append(("Customer-Bot", customer_bot_process))
        print("✅ Started: Customer-Bot (@BazaarOpsCustomerHelpBot)")
        time.sleep(2)
        
        # 6. Start AI Scheduler
        print("🧠 Starting AI Agent Scheduler...")
        scheduler_process = subprocess.Popen(
            [sys.executable, "scheduler.py"],
            cwd=str(BASE_DIR / "telegram-bots" / "owner-bot"),
            shell=True
        )
        processes.append(("Claude-AI-Scheduler", scheduler_process))
        print("✅ Started: Claude-AI-Scheduler")
        
        print("\n" + "=" * 70)
        print("🎉 All Backend Services Running Successfully!")
        print("=" * 70)
        print("\n📱 Access Points:")
        print("   • Owner API: http://localhost:8001")
        print("   • Customer API: http://localhost:8002")
        print("   • Agent API: http://localhost:8003")
        print("   • Owner Bot: @BazaarOpsAdminBot")
        print("   • Customer Bot: @BazaarOpsCustomerHelpBot")
        print("\n💡 Dashboard:")
        print("   • Run separately: cd owner-dashboard && npm run dev")
        print("   • Access at: http://localhost:3000")
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
        print("   • Customer ordering via Telegram (deep linking)")
        print("   • Automatic inventory reduction on orders")
        print("   • Auto-notifications on delivery")
        print("   • WhatsApp supplier integration")
        print("\n🔗 Customer Deep Linking:")
        print("   Share: https://t.me/BazaarOpsCustomerHelpBot?start=YOUR_STORE_ID")
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

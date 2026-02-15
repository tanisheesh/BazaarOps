"""
Customer Bot with HTTP Server for Render Free Tier
Runs bot + dummy HTTP server on PORT
"""
import os
import asyncio
from threading import Thread
from flask import Flask
from bot import main as run_bot

# Get PORT from Render
PORT = int(os.getenv("PORT", 8080))

# Create Flask app for health checks
app = Flask(__name__)

@app.route('/')
def home():
    return {"status": "running", "service": "customer-bot"}

@app.route('/health')
def health():
    return {"status": "healthy"}

def run_flask():
    """Run Flask in background"""
    app.run(host='0.0.0.0', port=PORT)

def run_telegram_bot():
    """Run Telegram bot"""
    run_bot()

if __name__ == "__main__":
    print(f"🚀 Starting Customer Bot on port {PORT}")
    
    # Start Flask in background thread
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    print(f"✅ HTTP server running on port {PORT}")
    print("🤖 Starting Telegram bot...")
    
    # Run bot in main thread
    run_telegram_bot()

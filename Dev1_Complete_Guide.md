# 🎓 DEV 1 COMPLETE GUIDE - Owner Dashboard & Service
## Absolute Beginner's Edition - From Zero to Working System

**Your Mission:** Build the owner dashboard (Next.js), owner service API (FastAPI), and owner notification bot.

**Time:** 8-10 hours total  
**Difficulty:** Beginner-friendly (every step explained!)

---

## 📋 OVERVIEW - What You'll Build

```
DAY 1 (Morning - 2 hours):
├── ✅ Get database credentials from Dev 2
├── ✅ Set up Python environment
├── ✅ Build Owner Service API
└── ✅ Test API endpoints

DAY 1 (Afternoon - 3 hours):
├── ✅ Set up Next.js project
├── ✅ Build Dashboard Home page
├── ✅ Build Inventory page
└── ✅ Build Orders page

DAY 2 (Morning - 2 hours):
├── ✅ Connect Dashboard to API
├── ✅ Test all features
└── ✅ Add real-time updates

DAY 2 (Afternoon - 2 hours):
├── ✅ Create Owner Notification Bot
├── ✅ Test complete system
└── ✅ Prepare demo
```

---

## 🚀 PHASE 0: GET CREDENTIALS FROM DEV 2 (15 minutes)

### What You Need

**WAIT for Dev 2 to finish Phase 1 (Database Setup) first!**

Dev 2 will share a file called `credentials.txt` with you. It should contain:

```
SUPABASE_URL=https://abcdefgh.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
STORE_ID=550e8400-e29b-41d4-a716-446655440000
```

**Actions:**

1. **Get credentials.txt from Dev 2** (via Slack/WhatsApp/Email)
2. **Save it on your Desktop**
3. **Verify you have all 3 values**

✅ You're ready to start!

---

## 🐍 PHASE 1: OWNER SERVICE API (2.5 hours)

### Step 1.1: Install Python (10 minutes)

**What is Python?**
A programming language we'll use for the backend API.

**Actions:**

1. **Open Terminal:**
   - **Mac:** Press Cmd+Space, type "Terminal", Enter
   - **Windows:** Press Windows key, type "cmd", Enter

2. **Check if Python is installed:**
   ```bash
   python3 --version
   ```

3. **What you'll see:**
   - ✅ "Python 3.8.x" or higher = Good!
   - ❌ "command not found" = Need to install

4. **If you need to install:**
   - Go to: https://www.python.org/downloads/
   - Click "Download Python 3.x"
   - Run installer
   - **IMPORTANT:** Check "Add Python to PATH"
   - Restart Terminal

✅ Python installed!

---

### Step 1.2: Create Project Folders (5 minutes)

**Actions:**

1. **In Terminal, type these commands:**

```bash
# Create main folder
mkdir bazaarops
cd bazaarops

# Create your folders
mkdir owner-service
mkdir owner-dashboard

# Check it worked
ls
```

You should see: `owner-service  owner-dashboard`

✅ Folders created!

---

### Step 1.3: Set Up Owner Service (20 minutes)

**Actions:**

1. **Go into owner-service folder:**
   ```bash
   cd owner-service
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```
   Wait 1-2 minutes.

3. **Activate virtual environment:**
   
   **Mac/Linux:**
   ```bash
   source venv/bin/activate
   ```
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   You should see `(venv)` in your prompt!

4. **Create requirements.txt:**
   
   **Mac/Linux:**
   ```bash
   cat > requirements.txt << 'EOF'
   fastapi==0.104.1
   uvicorn==0.24.0
   supabase==2.0.3
   python-dotenv==1.0.0
   httpx==0.25.0
   pydantic==2.5.0
   EOF
   ```
   
   **Windows:**
   - Open Notepad
   - Paste:
     ```
     fastapi==0.104.1
     uvicorn==0.24.0
     supabase==2.0.3
     python-dotenv==1.0.0
     httpx==0.25.0
     pydantic==2.5.0
     ```
   - Save as `requirements.txt` in owner-service folder

5. **Install packages:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Takes 2-3 minutes. Lots of text = normal!

6. **Create .env file:**
   
   Open Notepad/TextEdit and create a file with your actual credentials:
   
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   STORE_ID=550e8400-e29b-41d4-a716-446655440000
   ```
   
   Save as `.env` in owner-service folder

✅ Owner service environment ready!

---

### Step 1.4: Create Basic API (30 minutes)

**What is an API?**
The middleman between your dashboard and database. Dashboard asks API for data, API gets it from database.

**Actions:**

1. **Create main.py:**
   
   **Mac/Linux:**
   ```bash
   touch main.py
   ```
   
   **Windows:**
   - Right-click in folder
   - New → Text Document
   - Name it `main.py`

2. **Open main.py in text editor** (Notepad, TextEdit, VS Code)

3. **Paste this code:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="BazaarOps Owner Service",
    description="Owner-facing service for store management",
    version="1.0.0"
)

# Enable CORS (so Next.js can talk to us)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint - test if service is running
@app.get("/")
async def root():
    return {
        "service": "owner-service",
        "status": "running",
        "message": "Owner Service is live!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

4. **Save the file**

5. **Test it:**
   ```bash
   python main.py
   ```

6. **You should see:**
   ```
   INFO:     Started server process
   INFO:     Uvicorn running on http://0.0.0.0:8001
   ```

7. **Open browser:**
   - Go to: http://localhost:8001
   - Should see: `{"service": "owner-service", "status": "running"...}`

8. **Press Ctrl+C to stop**

✅ Basic API works!

---

### Step 1.5: Add Database Service (45 minutes)

**Actions:**

1. **Create folders:**
   ```bash
   mkdir services
   mkdir routers
   mkdir models
   ```

2. **Create __init__.py files:**
   
   **Mac/Linux:**
   ```bash
   touch services/__init__.py
   touch routers/__init__.py
   touch models/__init__.py
   ```
   
   **Windows:**
   - Create empty text files named `__init__.py` in each folder

3. **Create services/db_service.py:**

```python
from supabase import create_client, Client
import os

# Connect to Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class OwnerDatabaseService:
    """Database operations for store owners"""
    
    @staticmethod
    def get_inventory(store_id: str):
        """Get all inventory with product details"""
        try:
            response = supabase.table("inventory")\
                .select("*, products(id, name, description, unit, category_id, categories(name))")\
                .eq("store_id", store_id)\
                .order("products(name)")\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting inventory: {e}")
            return []
    
    @staticmethod
    def update_inventory(store_id: str, product_id: str, quantity: float):
        """Update inventory quantity"""
        try:
            response = supabase.table("inventory")\
                .update({"quantity": quantity, "updated_at": "now()"})\
                .eq("store_id", store_id)\
                .eq("product_id", product_id)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error updating inventory: {e}")
            return None
    
    @staticmethod
    def get_orders(store_id: str, limit: int = 50):
        """Get recent orders"""
        try:
            response = supabase.table("orders")\
                .select("*, customers(name, phone)")\
                .eq("store_id", store_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting orders: {e}")
            return []
    
    @staticmethod
    def update_order_status(order_id: str, status: str):
        """Update order status"""
        try:
            response = supabase.table("orders")\
                .update({"status": status, "updated_at": "now()"})\
                .eq("id", order_id)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error updating order: {e}")
            return None
    
    @staticmethod
    def get_dashboard_stats(store_id: str):
        """Get dashboard statistics"""
        from datetime import datetime
        
        try:
            today = datetime.now().date()
            
            # Get today's orders
            orders_response = supabase.table("orders")\
                .select("total_amount, created_at, status")\
                .eq("store_id", store_id)\
                .gte("created_at", today.isoformat())\
                .execute()
            
            total_orders = len(orders_response.data)
            total_revenue = sum(
                float(o["total_amount"]) 
                for o in orders_response.data
            )
            
            # Get low stock items
            inventory_response = supabase.table("inventory")\
                .select("quantity, reorder_threshold, products(name)")\
                .eq("store_id", store_id)\
                .execute()
            
            low_stock_items = [
                {
                    "name": item["products"]["name"],
                    "quantity": float(item["quantity"]),
                    "threshold": float(item["reorder_threshold"])
                }
                for item in inventory_response.data
                if float(item["quantity"]) < float(item["reorder_threshold"])
            ]
            
            return {
                "today_orders": total_orders,
                "today_revenue": total_revenue,
                "low_stock_count": len(low_stock_items),
                "low_stock_items": low_stock_items
            }
        except Exception as e:
            print(f"❌ Error getting dashboard stats: {e}")
            return {
                "today_orders": 0,
                "today_revenue": 0,
                "low_stock_count": 0,
                "low_stock_items": []
            }
    
    @staticmethod
    def get_customers(store_id: str):
        """Get all customers"""
        try:
            response = supabase.table("customers")\
                .select("*")\
                .eq("store_id", store_id)\
                .order("name")\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting customers: {e}")
            return []

# Create instance
db = OwnerDatabaseService()
```

4. **Save the file**

✅ Database service created!

---

### Step 1.6: Add API Endpoints (45 minutes)

**Actions:**

1. **Create routers/owner.py:**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.db_service import db
import os

router = APIRouter(prefix="/api/owner", tags=["owner"])

# Data models
class InventoryUpdate(BaseModel):
    product_id: str
    quantity: float

class OrderStatusUpdate(BaseModel):
    status: str

# Dashboard endpoint
@router.get("/dashboard/{store_id}")
async def get_dashboard(store_id: str):
    """
    Get dashboard statistics
    
    Returns: today's orders, revenue, low stock items
    """
    print(f"📊 Getting dashboard stats for store: {store_id}")
    
    stats = db.get_dashboard_stats(store_id)
    
    return stats

# Inventory endpoints
@router.get("/inventory/{store_id}")
async def get_inventory(store_id: str):
    """
    Get all inventory for a store
    
    Returns: list of products with stock levels
    """
    print(f"📦 Getting inventory for store: {store_id}")
    
    inventory = db.get_inventory(store_id)
    
    # Format response
    formatted_inventory = []
    for item in inventory:
        product = item.get("products", {})
        category = product.get("categories", {})
        
        formatted_inventory.append({
            "inventory_id": item["id"],
            "product_id": item["product_id"],
            "product_name": product.get("name", "Unknown"),
            "description": product.get("description", ""),
            "category": category.get("name", "Uncategorized"),
            "quantity": float(item["quantity"]),
            "unit": product.get("unit", "piece"),
            "unit_price": float(item["unit_price"]),
            "reorder_threshold": float(item["reorder_threshold"]),
            "status": "low" if float(item["quantity"]) < float(item["reorder_threshold"]) else "ok"
        })
    
    return {
        "success": True,
        "inventory": formatted_inventory,
        "count": len(formatted_inventory)
    }

@router.post("/inventory/{store_id}/update")
async def update_inventory(store_id: str, update: InventoryUpdate):
    """
    Update inventory quantity
    
    Body: {
        "product_id": "abc-123",
        "quantity": 50.5
    }
    """
    print(f"📝 Updating inventory: {update.product_id} to {update.quantity}")
    
    result = db.update_inventory(store_id, update.product_id, update.quantity)
    
    if not result:
        raise HTTPException(status_code=500, detail="Could not update inventory")
    
    return {
        "success": True,
        "message": "Inventory updated",
        "data": result
    }

# Orders endpoints
@router.get("/orders/{store_id}")
async def get_orders(store_id: str, limit: int = 50):
    """
    Get recent orders
    
    Query params: limit (default 50)
    """
    print(f"📋 Getting orders for store: {store_id}")
    
    orders = db.get_orders(store_id, limit)
    
    # Format response
    formatted_orders = []
    for order in orders:
        customer = order.get("customers", {})
        
        formatted_orders.append({
            "order_id": order["id"],
            "customer_name": customer.get("name", "Unknown"),
            "customer_phone": customer.get("phone", ""),
            "total_amount": float(order["total_amount"]),
            "status": order["status"],
            "payment_status": order["payment_status"],
            "created_at": order["created_at"],
            "notes": order.get("notes", "")
        })
    
    return {
        "success": True,
        "orders": formatted_orders,
        "count": len(formatted_orders)
    }

@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, update: OrderStatusUpdate):
    """
    Update order status
    
    Body: {
        "status": "completed"
    }
    
    Valid statuses: pending, confirmed, completed, cancelled
    """
    print(f"📝 Updating order {order_id} to {update.status}")
    
    valid_statuses = ["pending", "confirmed", "completed", "cancelled"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    result = db.update_order_status(order_id, update.status)
    
    if not result:
        raise HTTPException(status_code=500, detail="Could not update order")
    
    return {
        "success": True,
        "message": "Order status updated",
        "data": result
    }

# Customers endpoint
@router.get("/customers/{store_id}")
async def get_customers(store_id: str):
    """Get all customers"""
    print(f"👥 Getting customers for store: {store_id}")
    
    customers = db.get_customers(store_id)
    
    return {
        "success": True,
        "customers": customers,
        "count": len(customers)
    }

# Notification endpoint (for agent service to call)
@router.post("/notify")
async def notify_owner(store_id: str, message: str):
    """
    Receive notification from agent service
    
    Body: {
        "store_id": "abc-123",
        "message": "New order received!"
    }
    """
    print(f"🔔 Notification for store {store_id}: {message}")
    
    # In real implementation, send to Telegram bot
    # For now, just log it
    
    return {
        "success": True,
        "message": "Notification received"
    }
```

2. **Save the file**

3. **Update main.py to include routes:**
   
   Add near the top:
   ```python
   from routers import owner
   ```
   
   Add after creating app:
   ```python
   app.include_router(owner.router)
   ```

4. **Complete main.py should look like:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import owner  # NEW!
import os

load_dotenv()

app = FastAPI(
    title="BazaarOps Owner Service",
    description="Owner-facing service for store management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include owner routes
app.include_router(owner.router)  # NEW!

@app.get("/")
async def root():
    return {
        "service": "owner-service",
        "status": "running",
        "message": "Owner Service is live!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

5. **Test the complete API:**
   ```bash
   python main.py
   ```

6. **Open browser:**
   - Go to: http://localhost:8001/docs
   - You'll see Swagger UI!
   - Try "GET /api/owner/dashboard/{store_id}"
   - Enter your STORE_ID
   - Click "Execute"
   - Should see dashboard stats! 🎉

✅ **PHASE 1 COMPLETE!** Owner Service API working!

---

## 🎨 PHASE 2: NEXT.JS DASHBOARD (4 hours)

### Step 2.1: Install Node.js (15 minutes)

**What is Node.js?**
JavaScript runtime - needed to run Next.js.

**Actions:**

1. **Check if Node.js is installed:**
   ```bash
   node --version
   ```

2. **What you'll see:**
   - ✅ "v18.x" or higher = Good!
   - ❌ "command not found" = Need to install

3. **If you need to install:**
   - Go to: https://nodejs.org/
   - Download "LTS" version
   - Run installer
   - Restart Terminal

✅ Node.js installed!

---

### Step 2.2: Create Next.js Project (20 minutes)

**Actions:**

1. **Go to owner-dashboard folder:**
   ```bash
   cd ..  # Go back to bazaarops folder
   cd owner-dashboard
   ```

2. **Create Next.js app:**
   ```bash
   npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
   ```
   
   It will ask questions:
   - "Would you like to use ESLint?" → Yes
   - "Would you like to use Turbopack?" → No
   
   Wait 2-3 minutes for installation.

3. **Install additional packages:**
   ```bash
   npm install axios
   ```

4. **Create .env.local file:**
   
   Create a file named `.env.local` in owner-dashboard folder:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8001
   NEXT_PUBLIC_STORE_ID=your-store-id-here
   ```

5. **Test Next.js works:**
   ```bash
   npm run dev
   ```
   
   Open browser: http://localhost:3000
   
   Should see Next.js default page!
   
   Press Ctrl+C to stop.

✅ Next.js project created!

---

### Step 2.3: Create Dashboard Home Page (1 hour)

**Actions:**

1. **Open app/page.tsx**

2. **Replace everything with:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface DashboardStats {
  today_orders: number
  today_revenue: number
  low_stock_count: number
  low_stock_items: Array<{
    name: string
    quantity: number
    threshold: number
  }>
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
  const STORE_ID = process.env.NEXT_PUBLIC_STORE_ID

  useEffect(() => {
    fetchStats()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/owner/dashboard/${STORE_ID}`)
      const data = await response.json()
      setStats(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching stats:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            🛒 BazaarOps Dashboard
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Welcome back! Here's your store overview
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Today's Orders */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Today's Orders</p>
                <p className="text-3xl font-bold text-blue-600">
                  {stats?.today_orders || 0}
                </p>
              </div>
              <div className="text-4xl">📦</div>
            </div>
          </div>

          {/* Today's Revenue */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Today's Revenue</p>
                <p className="text-3xl font-bold text-green-600">
                  ₹{stats?.today_revenue.toFixed(2) || 0}
                </p>
              </div>
              <div className="text-4xl">💰</div>
            </div>
          </div>

          {/* Low Stock */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Low Stock Items</p>
                <p className="text-3xl font-bold text-orange-600">
                  {stats?.low_stock_count || 0}
                </p>
              </div>
              <div className="text-4xl">⚠️</div>
            </div>
          </div>
        </div>

        {/* Low Stock Alert */}
        {stats && stats.low_stock_count > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 mb-8">
            <h3 className="text-lg font-semibold text-orange-900 mb-4 flex items-center">
              <span className="text-2xl mr-2">⚠️</span>
              Low Stock Alert
            </h3>
            <div className="space-y-3">
              {stats.low_stock_items.map((item, index) => (
                <div 
                  key={index}
                  className="flex justify-between items-center bg-white p-3 rounded border border-orange-200"
                >
                  <span className="font-medium text-orange-900">{item.name}</span>
                  <span className="text-orange-700">
                    {item.quantity.toFixed(1)} / {item.threshold.toFixed(1)} (threshold)
                  </span>
                </div>
              ))}
            </div>
            <Link 
              href="/inventory"
              className="inline-block mt-4 text-orange-700 hover:text-orange-900 font-medium"
            >
              Go to Inventory →
            </Link>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link 
            href="/inventory" 
            className="bg-blue-600 hover:bg-blue-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">📦</div>
            <div className="font-semibold">Inventory</div>
          </Link>
          
          <Link 
            href="/orders" 
            className="bg-green-600 hover:bg-green-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">🛒</div>
            <div className="font-semibold">Orders</div>
          </Link>
          
          <Link 
            href="/customers" 
            className="bg-purple-600 hover:bg-purple-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">👥</div>
            <div className="font-semibold">Customers</div>
          </Link>
          
          <button 
            onClick={fetchStats}
            className="bg-gray-600 hover:bg-gray-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">🔄</div>
            <div className="font-semibold">Refresh</div>
          </button>
        </div>
      </main>
    </div>
  )
}
```

3. **Save the file**

✅ Dashboard home page created!

---

### Step 2.4: Create Inventory Page (1 hour)

**Actions:**

1. **Create app/inventory/page.tsx:**
   ```bash
   mkdir app/inventory
   touch app/inventory/page.tsx
   ```

2. **Open app/inventory/page.tsx and paste:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface InventoryItem {
  inventory_id: string
  product_id: string
  product_name: string
  description: string
  category: string
  quantity: number
  unit: string
  unit_price: number
  reorder_threshold: number
  status: string
}

export default function Inventory() {
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editQuantity, setEditQuantity] = useState<string>('')
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
  const STORE_ID = process.env.NEXT_PUBLIC_STORE_ID

  useEffect(() => {
    fetchInventory()
  }, [])

  const fetchInventory = async () => {
    try {
      const response = await fetch(`${API_URL}/api/owner/inventory/${STORE_ID}`)
      const data = await response.json()
      setInventory(data.inventory || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching inventory:', error)
      setLoading(false)
    }
  }

  const startEdit = (item: InventoryItem) => {
    setEditingId(item.product_id)
    setEditQuantity(item.quantity.toString())
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditQuantity('')
  }

  const saveEdit = async (productId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/inventory/${STORE_ID}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId,
          quantity: parseFloat(editQuantity)
        })
      })
      
      if (response.ok) {
        await fetchInventory()
        setEditingId(null)
        setEditQuantity('')
      }
    } catch (error) {
      console.error('Error updating inventory:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading inventory...</div>
      </div>
    )
  }

  const lowStockItems = inventory.filter(item => item.status === 'low')
  const okItems = inventory.filter(item => item.status === 'ok')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">📦 Inventory</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage your stock levels
              </p>
            </div>
            <Link 
              href="/"
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Total Products</p>
            <p className="text-3xl font-bold text-blue-600">{inventory.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">In Stock</p>
            <p className="text-3xl font-bold text-green-600">{okItems.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Low Stock</p>
            <p className="text-3xl font-bold text-orange-600">{lowStockItems.length}</p>
          </div>
        </div>

        {/* Inventory Table */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Product
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stock
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {inventory.map((item) => (
                  <tr key={item.product_id} className={item.status === 'low' ? 'bg-orange-50' : ''}>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{item.product_name}</div>
                      {item.description && (
                        <div className="text-sm text-gray-500">{item.description}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {item.category}
                    </td>
                    <td className="px-6 py-4">
                      {editingId === item.product_id ? (
                        <input
                          type="number"
                          value={editQuantity}
                          onChange={(e) => setEditQuantity(e.target.value)}
                          className="w-20 px-2 py-1 border border-gray-300 rounded"
                          step="0.1"
                        />
                      ) : (
                        <span className="font-medium">
                          {item.quantity.toFixed(1)} {item.unit}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      ₹{item.unit_price.toFixed(2)}/{item.unit}
                    </td>
                    <td className="px-6 py-4">
                      {item.status === 'low' ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                          ⚠️ Low Stock
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✅ In Stock
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {editingId === item.product_id ? (
                        <div className="flex space-x-2">
                          <button
                            onClick={() => saveEdit(item.product_id)}
                            className="text-green-600 hover:text-green-800 font-medium text-sm"
                          >
                            Save
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(item)}
                          className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
```

3. **Save the file**

✅ Inventory page created!

---

### Step 2.5: Create Orders Page (1 hour)

**Actions:**

1. **Create app/orders/page.tsx:**
   ```bash
   mkdir app/orders
   touch app/orders/page.tsx
   ```

2. **Open app/orders/page.tsx and paste:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Order {
  order_id: string
  customer_name: string
  customer_phone: string
  total_amount: number
  status: string
  payment_status: string
  created_at: string
  notes: string
}

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
  const STORE_ID = process.env.NEXT_PUBLIC_STORE_ID

  useEffect(() => {
    fetchOrders()
    
    // Refresh every 10 seconds
    const interval = setInterval(fetchOrders, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${STORE_ID}`)
      const data = await response.json()
      setOrders(data.orders || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching orders:', error)
      setLoading(false)
    }
  }

  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${orderId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })
      
      if (response.ok) {
        await fetchOrders()
      }
    } catch (error) {
      console.error('Error updating order:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'confirmed': return 'bg-blue-100 text-blue-800'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'cancelled': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredOrders = filter === 'all' 
    ? orders 
    : orders.filter(order => order.status === filter)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading orders...</div>
      </div>
    )
  }

  const pendingCount = orders.filter(o => o.status === 'pending').length
  const completedCount = orders.filter(o => o.status === 'completed').length

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">🛒 Orders</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage customer orders
              </p>
            </div>
            <Link 
              href="/"
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Total Orders</p>
            <p className="text-3xl font-bold text-blue-600">{orders.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Pending</p>
            <p className="text-3xl font-bold text-yellow-600">{pendingCount}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Completed</p>
            <p className="text-3xl font-bold text-green-600">{completedCount}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Total Revenue</p>
            <p className="text-3xl font-bold text-green-600">
              ₹{orders.reduce((sum, o) => sum + o.total_amount, 0).toFixed(2)}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6 flex space-x-2">
          {['all', 'pending', 'confirmed', 'completed'].map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-4 py-2 rounded-lg font-medium ${
                filter === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* Orders List */}
        <div className="space-y-4">
          {filteredOrders.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center text-gray-500">
              No orders found
            </div>
          ) : (
            filteredOrders.map((order) => (
              <div key={order.order_id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Order #{order.order_id.substring(0, 8)}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status.toUpperCase()}
                      </span>
                      {order.payment_status === 'unpaid' && (
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          CREDIT
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div>
                        <p className="text-sm text-gray-600">Customer</p>
                        <p className="font-medium text-gray-900">{order.customer_name}</p>
                        <p className="text-sm text-gray-600">{order.customer_phone}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Total Amount</p>
                        <p className="text-2xl font-bold text-green-600">₹{order.total_amount.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Order Date</p>
                        <p className="font-medium text-gray-900">
                          {new Date(order.created_at).toLocaleString('en-IN')}
                        </p>
                      </div>
                      {order.notes && (
                        <div>
                          <p className="text-sm text-gray-600">Notes</p>
                          <p className="text-gray-900">{order.notes}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="ml-6 flex flex-col space-y-2">
                    {order.status === 'pending' && (
                      <button
                        onClick={() => updateOrderStatus(order.order_id, 'confirmed')}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                      >
                        Confirm
                      </button>
                    )}
                    {order.status === 'confirmed' && (
                      <button
                        onClick={() => updateOrderStatus(order.order_id, 'completed')}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium"
                      >
                        Complete
                      </button>
                    )}
                    {order.status !== 'cancelled' && order.status !== 'completed' && (
                      <button
                        onClick={() => updateOrderStatus(order.order_id, 'cancelled')}
                        className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  )
}
```

3. **Save the file**

✅ Orders page created!

---

### Step 2.6: Create Customers Page (30 minutes)

**Actions:**

1. **Create app/customers/page.tsx:**
   ```bash
   mkdir app/customers
   touch app/customers/page.tsx
   ```

2. **Paste this simple version:**

```typescript
'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Customer {
  id: string
  name: string
  phone: string
  address: string
  created_at: string
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
  const STORE_ID = process.env.NEXT_PUBLIC_STORE_ID

  useEffect(() => {
    fetchCustomers()
  }, [])

  const fetchCustomers = async () => {
    try {
      const response = await fetch(`${API_URL}/api/owner/customers/${STORE_ID}`)
      const data = await response.json()
      setCustomers(data.customers || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching customers:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading customers...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">👥 Customers</h1>
              <p className="text-sm text-gray-600 mt-1">Your customer list</p>
            </div>
            <Link 
              href="/"
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Total Customers: {customers.length}</h2>
          <div className="space-y-3">
            {customers.map((customer) => (
              <div key={customer.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">{customer.name}</p>
                    <p className="text-sm text-gray-600">{customer.phone}</p>
                    {customer.address && (
                      <p className="text-sm text-gray-500 mt-1">{customer.address}</p>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    Joined: {new Date(customer.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
```

3. **Save the file**

✅ **PHASE 2 COMPLETE!** Dashboard is ready!

---

## 🧪 PHASE 3: TEST EVERYTHING TOGETHER (30 minutes)

### Full System Test

**You need 2 Terminal windows:**

**Terminal 1 - Owner Service:**
```bash
cd bazaarops/owner-service
source venv/bin/activate
python main.py
```

**Terminal 2 - Next.js Dashboard:**
```bash
cd bazaarops/owner-dashboard
npm run dev
```

**Both running? Test the dashboard!**

1. **Open browser: http://localhost:3000**
   - Should see dashboard with stats
   - Should see today's orders, revenue, low stock

2. **Click "Inventory"**
   - Should see all products
   - Try editing quantity
   - Click Save
   - Should update!

3. **Click "Orders"**
   - Should see all orders
   - Try changing status
   - Should update!

4. **Click "Customers"**
   - Should see customer list

**If all this works - PHASE 3 DONE! 🎉**

---

## 🤖 PHASE 4: OWNER NOTIFICATION BOT (1.5 hours)

### Step 4.1: Create Telegram Bot (15 minutes)

**Actions:**

1. **Open Telegram app**
2. **Search: @BotFather**
3. **Send: `/newbot`**
4. **Name: `BazaarOps Owner Bot`**
5. **Username: `bazaarops_owner_bot`**
6. **Copy token** (starts with numbers)
7. **Add to credentials.txt:**
   ```
   TELEGRAM_OWNER_BOT_TOKEN=123456789:ABCdef...
   ```

8. **Get your chat ID:**
   - Search for `@userinfobot` on Telegram
   - Send any message
   - It will reply with your user ID
   - Copy this number
   - Add to credentials.txt:
     ```
     OWNER_CHAT_ID=123456789
     ```

✅ Owner bot created!

---

### Step 4.2: Build Notification Bot (45 minutes)

**Actions:**

1. **Create telegram-bots folder:**
   ```bash
   cd ..  # Back to bazaarops
   mkdir -p telegram-bots/owner-bot
   cd telegram-bots/owner-bot
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate
   ```

3. **Create requirements.txt:**
   ```
   python-telegram-bot==20.7
   python-dotenv==1.0.0
   fastapi==0.104.1
   uvicorn==0.24.0
   ```

4. **Install:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create .env:**
   ```
   TELEGRAM_OWNER_BOT_TOKEN=your-token
   OWNER_CHAT_ID=your-chat-id
   ```

6. **Create bot.py:**

```python
from telegram import Bot
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize bot
bot = Bot(token=os.getenv("TELEGRAM_OWNER_BOT_TOKEN"))
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")

# Create FastAPI app for receiving notifications
app = FastAPI(title="Owner Notification Bot")

class Notification(BaseModel):
    store_id: str
    message: str

@app.post("/notify")
async def send_notification(notification: Notification):
    """Receive notification and send to owner"""
    try:
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=notification.message,
            parse_mode='Markdown'
        )
        return {"success": True}
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return {"service": "owner-notification-bot", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
```

7. **Test it:**
   ```bash
   python bot.py
   ```

8. **Test notification (in another terminal):**
   ```bash
   curl -X POST http://localhost:8004/notify \
     -H "Content-Type: application/json" \
     -d '{"store_id": "test", "message": "🎉 Test notification!"}'
   ```

9. **Check Telegram - you should get a message!**

✅ **PHASE 4 COMPLETE!** Owner bot working!

---

## 🔗 PHASE 5: FINAL INTEGRATION (30 minutes)

### Connect to Dev 2's Services

**Get from Dev 2:**
- Customer Service URL: `http://localhost:8002`
- Agent Service URL: `http://localhost:8003`

### Test Complete Flow

**Terminal Setup (need 4!):**

**Terminal 1 - Owner Service:**
```bash
cd bazaarops/owner-service
source venv/bin/activate
python main.py
```

**Terminal 2 - Owner Dashboard:**
```bash
cd bazaarops/owner-dashboard
npm run dev
```

**Terminal 3 - Owner Bot:**
```bash
cd bazaarops/telegram-bots/owner-bot
source venv/bin/activate
python bot.py
```

**Terminal 4 - Watch Dev 2's services:**
Ask Dev 2 to have their services running!

**Now test:**

1. **Ask Dev 2 to place an order via their bot**
2. **Watch your dashboard - order should appear!**
3. **Refresh orders page - new order there**
4. **Check inventory - stock reduced**
5. **You might get Telegram notification!**

✅ **PHASE 5 COMPLETE!** Everything integrated!

---

## 🎬 PHASE 6: DEMO PREPARATION (30 minutes)

### Your Demo Script (2-3 minutes)

**Setup Before Demo:**
- All services running
- Dashboard open in browser
- Supabase dashboard open (separate tab)
- Be on Orders page

**Demo Flow:**

**Minute 1: Show Architecture**
"We built microservices:
- Owner Service (Port 8001) - My API
- Owner Dashboard (Port 3000) - My Next.js app
- Owner Bot (Port 8004) - Notifications
- Works with Dev 2's Customer & Agent services"

**Minute 2: Live Dashboard Demo**
1. Show home page - stats
2. Click Inventory - show products
3. Edit quantity - live update
4. Show Orders page
5. Show order status updates

**Minute 3: Integration**
1. Ask Dev 2 to place order
2. Show order appear in real-time
3. Show inventory update
4. Update order status
5. Show professional UI

### Practice Run

Before hackathon:
1. Run through demo 3 times
2. Make sure all services start quickly
3. Have backup screenshots if something fails
4. Know your talking points

---

## ✅ FINAL CHECKLIST

### Phase 1: Owner Service
- [ ] Python installed
- [ ] Virtual environment created
- [ ] All packages installed
- [ ] .env file configured
- [ ] Service runs on port 8001
- [ ] All API endpoints work
- [ ] Can access /docs

### Phase 2: Dashboard
- [ ] Node.js installed
- [ ] Next.js project created
- [ ] Home page shows stats
- [ ] Inventory page works
- [ ] Can edit quantities
- [ ] Orders page works
- [ ] Can update statuses
- [ ] Customers page works
- [ ] Connects to API successfully

### Phase 3: Integration
- [ ] Dashboard loads data from API
- [ ] Real-time updates work
- [ ] All pages navigate correctly
- [ ] Data displays properly
- [ ] No CORS errors

### Phase 4: Notification Bot
- [ ] Bot created on Telegram
- [ ] Bot service runs on port 8004
- [ ] Can send test notification
- [ ] Receives notifications successfully

### Phase 5: Full Integration
- [ ] Works with Dev 2's services
- [ ] Orders appear from customer bot
- [ ] Inventory updates automatically
- [ ] Can manage entire flow

### Phase 6: Demo Ready
- [ ] All services start quickly
- [ ] Demo script practiced
- [ ] Know what to show
- [ ] Backup plan ready

---

## 🚨 TROUBLESHOOTING

### "Module not found"
```bash
# Check venv is activated
source venv/bin/activate

# Reinstall
pip install -r requirements.txt  # Python
npm install  # Node.js
```

### "Port already in use"
```bash
# Find what's using port
lsof -i :8001  # Mac
netstat -ano | findstr :8001  # Windows

# Kill process
kill -9 <PID>  # Mac
taskkill /PID <PID> /F  # Windows
```

### "CORS error"
- Make sure owner-service has CORS enabled
- Check API_URL in .env.local is correct
- Restart both services

### Dashboard not loading data
- Check .env.local has correct API_URL
- Check STORE_ID is correct
- Check owner-service is running
- Open browser console (F12) for errors

### Can't update inventory
- Check POST request in Network tab
- Verify STORE_ID matches
- Check owner-service logs

---

## 🏆 YOU'RE DONE!

You've built:
- ✅ Complete Owner Service API (REST)
- ✅ Professional Next.js Dashboard
- ✅ Inventory management
- ✅ Order management
- ✅ Customer list
- ✅ Real-time updates
- ✅ Telegram notification bot
- ✅ Full integration with Dev 2

**Now coordinate final testing with Dev 2! 🚀**

### Share with Dev 2:
1. Your API is on port 8001
2. Notification bot on port 8004
3. Dashboard on port 3000
4. Ready to receive orders!

**Good luck at the hackathon! 💪**

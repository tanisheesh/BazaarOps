# 🎓 DEV 2 COMPLETE GUIDE - Using Claude Agent SDK
## Absolute Beginner's Edition - From Zero to Working System

**Your Mission:** Build the database, customer service, customer bot, and AI agents using Claude Agent SDK.

**Time:** 8-10 hours total  
**Difficulty:** Beginner-friendly (every step explained!)

---

## 📋 OVERVIEW - What You'll Build

```
DAY 1 (Morning - 2 hours):
├── ✅ Create Supabase Database
├── ✅ Set up all 9 tables
└── ✅ Insert sample data

DAY 1 (Afternoon - 3 hours):
├── ✅ Install Python & tools
├── ✅ Build Customer Service API
└── ✅ Test API endpoints

DAY 2 (Morning - 3 hours):
├── ✅ Create Telegram Bot
├── ✅ Connect bot to API
└── ✅ Test ordering flow

DAY 2 (Afternoon - 2 hours):
├── ✅ Install Claude Agent SDK
├── ✅ Build AI Agents
└── ✅ Test complete system
```

---

## 🚀 PHASE 1: DATABASE SETUP (2 hours)

### Step 1.1: Create Supabase Account (10 minutes)

**What is Supabase?**
Think of it like Google Sheets, but for storing app data. Both you and Dev 1 will use the same database.

**Actions:**

1. **Open your web browser**
   - Type: https://supabase.com
   - Press Enter

2. **Sign up**
   - Click the green "Start your project" button
   - Click "Sign in with GitHub" (easiest)
   - Or use your email
   - Create account

3. **Verify email** (if using email signup)
   - Check your inbox
   - Click the verification link

✅ You now have a Supabase account!

---

### Step 1.2: Create a New Project (10 minutes)

**Actions:**

1. **Click "New Project"** (big green button)

2. **Fill in the form:**
   ```
   Project Name: bazaarops
   Database Password: BazaarOps@2025!
   Region: Mumbai (or Singapore - closest to India)
   ```
   
   **IMPORTANT:** Write down your password!

3. **Click "Create new project"**
   - Wait 2-3 minutes
   - You'll see "Setting up project..." with a progress bar
   - ☕ Get coffee while it sets up

4. **When setup completes:**
   - You'll see your project dashboard
   - Green checkmark = Ready!

✅ Your database is running in the cloud!

---

### Step 1.3: Save Your Credentials (5 minutes)

**What are credentials?**
Think of them as your database's username and password. You'll need these to connect to it.

**Actions:**

1. **In Supabase dashboard:**
   - Look at the left sidebar
   - Click the ⚙️ "Settings" icon (near bottom)
   - Click "API" in the submenu

2. **You'll see two important things:**
   ```
   Project URL: https://abcdefgh.supabase.co
   anon public key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Open Notepad** (Windows) or **TextEdit** (Mac)

4. **Copy and paste:**
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.your-long-key-here
   DATABASE_PASSWORD=BazaarOps@2025!
   ```
   
   Replace with YOUR actual values!

5. **Save this file as:** `credentials.txt`
   - Save it on your Desktop
   - You'll need this file A LOT

6. **SHARE with Dev 1:**
   - Send this file via Slack/WhatsApp/Email
   - They need these same credentials

✅ Credentials saved and shared!

---

### Step 1.4: Create Database Tables (45 minutes)

**What are tables?**
Like sheets in Excel. Each table stores different types of data:
- `stores` = Store information
- `products` = Items for sale
- `inventory` = How much stock
- `orders` = Customer orders
- etc.

**Actions:**

1. **Go back to Supabase dashboard**

2. **Click "SQL Editor"** in left sidebar
   - It's the icon that looks like `</>`

3. **Click "New query"** button

4. **Copy the ENTIRE text below** and paste it into the SQL Editor:

```sql
-- ============================================
-- SECTION 1: CREATE STORES TABLE
-- ============================================

CREATE TABLE stores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL,
  name TEXT NOT NULL,
  phone TEXT,
  address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

5. **Click "RUN" button** (or press Ctrl+Enter / Cmd+Enter)
   - You should see: "Success. No rows returned"
   - ✅ First table created!

6. **Clear the editor** (select all, delete)

7. **Now create the rest of the tables, ONE AT A TIME:**

**Categories Table:**
```sql
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, name)
);
```
Click RUN ✅

**Products Table:**
```sql
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  description TEXT,
  unit TEXT DEFAULT 'piece',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
Click RUN ✅

**Inventory Table:**
```sql
CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  quantity DECIMAL(10,2) DEFAULT 0,
  unit_price DECIMAL(10,2) NOT NULL,
  reorder_threshold DECIMAL(10,2) DEFAULT 10,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, product_id)
);
```
Click RUN ✅

**Customers Table:**
```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  telegram_id TEXT,
  address TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, phone)
);
```
Click RUN ✅

**Orders Table:**
```sql
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled')),
  total_amount DECIMAL(10,2) NOT NULL,
  payment_status TEXT DEFAULT 'unpaid' CHECK (payment_status IN ('paid', 'unpaid', 'partial')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```
Click RUN ✅

**Order Items Table:**
```sql
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id),
  product_name TEXT NOT NULL,
  quantity DECIMAL(10,2) NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```
Click RUN ✅

**Credit Ledger Table:**
```sql
CREATE TABLE credit_ledger (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  order_id UUID REFERENCES orders(id),
  type TEXT NOT NULL CHECK (type IN ('debit', 'credit')),
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  balance_after DECIMAL(10,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```
Click RUN ✅

**Broadcast Logs Table:**
```sql
CREATE TABLE broadcast_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  recipient_count INTEGER DEFAULT 0,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);
```
Click RUN ✅

8. **Verify all tables created:**
   - Click "Table Editor" in left sidebar
   - You should see 9 tables listed!

✅ All database tables created!

---

### Step 1.5: Enable Security (10 minutes)

**What is Row Level Security (RLS)?**
It makes sure Store A can't see Store B's data. Think of it as a privacy lock.

**Actions:**

1. **In SQL Editor, paste this:**

```sql
-- Enable RLS on all tables
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE broadcast_logs ENABLE ROW LEVEL SECURITY;
```

2. **Click RUN** ✅

3. **Now create security policies:**

```sql
-- Stores Policy
CREATE POLICY "Users can only access their stores"
  ON stores FOR ALL
  USING (auth.uid() = owner_id);

-- Categories Policy
CREATE POLICY "Store owners access their categories"
  ON categories FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Products Policy
CREATE POLICY "Store owners access their products"
  ON products FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Inventory Policy
CREATE POLICY "Store owners access their inventory"
  ON inventory FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Customers Policy
CREATE POLICY "Store owners access their customers"
  ON customers FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Orders Policy
CREATE POLICY "Store owners access their orders"
  ON orders FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Credit Ledger Policy
CREATE POLICY "Store owners access their credit ledger"
  ON credit_ledger FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));

-- Broadcast Logs Policy
CREATE POLICY "Store owners access their broadcasts"
  ON broadcast_logs FOR ALL
  USING (store_id IN (SELECT id FROM stores WHERE owner_id = auth.uid()));
```

4. **Click RUN** ✅

5. **Create indexes for speed:**

```sql
CREATE INDEX idx_products_store ON products(store_id);
CREATE INDEX idx_inventory_store ON inventory(store_id);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_credit_ledger_customer ON credit_ledger(customer_id);
CREATE INDEX idx_credit_ledger_store ON credit_ledger(store_id);
```

6. **Click RUN** ✅

✅ Security enabled!

---

### Step 1.6: Add Sample Data (30 minutes)

**Why sample data?**
So we can test everything. Empty database = nothing to test!

**Actions:**

1. **Insert a test store:**

```sql
INSERT INTO stores (owner_id, name, phone, address)
VALUES 
  ('550e8400-e29b-41d4-a716-446655440000', 'Ramesh Kirana Store', '9876543210', '123 MG Road, Bangalore')
RETURNING id;
```

2. **Click RUN**
   - You'll see an ID like: `abc-123-def-456-ghi`
   - **COPY THIS ID!** This is your STORE_ID
   - Paste it into your credentials.txt file:
     ```
     STORE_ID=abc-123-def-456-ghi
     ```

3. **Add categories** (replace YOUR_STORE_ID with your actual ID):

```sql
INSERT INTO categories (store_id, name)
VALUES 
  ('YOUR_STORE_ID', 'Grains'),
  ('YOUR_STORE_ID', 'Snacks'),
  ('YOUR_STORE_ID', 'Beverages');
```

4. **Click RUN** ✅

5. **Get category IDs:**

```sql
SELECT id, name FROM categories WHERE store_id = 'YOUR_STORE_ID';
```

6. **Click RUN**
   - You'll see 3 rows with IDs
   - Find "Grains" - copy its ID

7. **Add products** (replace IDs):

```sql
INSERT INTO products (store_id, category_id, name, description, unit)
VALUES 
  ('YOUR_STORE_ID', 'GRAINS_CATEGORY_ID', 'Atta', 'Wheat flour', 'kg'),
  ('YOUR_STORE_ID', 'GRAINS_CATEGORY_ID', 'Rice', 'Basmati rice', 'kg'),
  ('YOUR_STORE_ID', 'GRAINS_CATEGORY_ID', 'Sugar', 'White sugar', 'kg'),
  ('YOUR_STORE_ID', 'GRAINS_CATEGORY_ID', 'Dal', 'Toor dal', 'kg');
```

8. **Click RUN** ✅

9. **Get product IDs:**

```sql
SELECT id, name FROM products WHERE store_id = 'YOUR_STORE_ID';
```

10. **Add inventory** (replace IDs):

```sql
INSERT INTO inventory (store_id, product_id, quantity, unit_price, reorder_threshold)
VALUES 
  ('YOUR_STORE_ID', 'ATTA_PRODUCT_ID', 50.00, 40.00, 10.00),
  ('YOUR_STORE_ID', 'RICE_PRODUCT_ID', 30.00, 60.00, 10.00),
  ('YOUR_STORE_ID', 'SUGAR_PRODUCT_ID', 20.00, 45.00, 5.00),
  ('YOUR_STORE_ID', 'DAL_PRODUCT_ID', 25.00, 80.00, 10.00);
```

11. **Click RUN** ✅

12. **Add customers:**

```sql
INSERT INTO customers (store_id, name, phone, address)
VALUES 
  ('YOUR_STORE_ID', 'Rajesh Kumar', '9876543210', 'Near Temple'),
  ('YOUR_STORE_ID', 'Priya Sharma', '9876543211', 'Apartment 5B'),
  ('YOUR_STORE_ID', 'Amit Patel', '9876543212', 'Shop 12, Market');
```

13. **Click RUN** ✅

14. **Verify everything:**

```sql
-- View all your data
SELECT 
  p.name as product,
  i.quantity,
  i.unit_price,
  c.name as category
FROM inventory i
JOIN products p ON i.product_id = p.id
LEFT JOIN categories c ON p.category_id = c.id
WHERE i.store_id = 'YOUR_STORE_ID';
```

15. **Click RUN**
    - You should see 4 products with quantities!
    - If you see this, YOU'RE DONE with database! 🎉

✅ **PHASE 1 COMPLETE!**

---

## 🐍 PHASE 2: PYTHON SETUP (30 minutes)

### Step 2.1: Check if Python is Installed (5 minutes)

**What is Python?**
A programming language. We'll use it to build our services.

**Actions:**

1. **Open Terminal:**
   - **Mac:** Press Cmd+Space, type "Terminal", press Enter
   - **Windows:** Press Windows key, type "cmd", press Enter

2. **Type this and press Enter:**
   ```bash
   python3 --version
   ```

3. **What you'll see:**
   - ✅ If you see: "Python 3.8.x" or higher = Good!
   - ❌ If you see: "command not found" = Need to install

4. **If you need to install:**
   - Go to: https://www.python.org/downloads/
   - Click "Download Python 3.x"
   - Run the installer
   - **IMPORTANT:** Check "Add Python to PATH" during install
   - Restart Terminal after installing

✅ Python is installed!

---

### Step 2.2: Create Project Folders (5 minutes)

**Actions:**

1. **In Terminal, type these commands one by one:**

```bash
# Create main folder
mkdir bazaarops
cd bazaarops

# Create subfolders
mkdir customer-service
mkdir agent-service
mkdir telegram-bots

# Check it worked
ls
```

You should see: `customer-service  agent-service  telegram-bots`

✅ Folders created!

---

### Step 2.3: Set Up Customer Service (20 minutes)

**Actions:**

1. **Go into customer-service folder:**
   ```bash
   cd customer-service
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```
   
   Wait 1-2 minutes. This creates a clean Python space.

3. **Activate virtual environment:**
   
   **Mac/Linux:**
   ```bash
   source venv/bin/activate
   ```
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   You should see `(venv)` before your prompt now!

4. **Create requirements.txt file:**
   
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
   - Save as `requirements.txt` in customer-service folder

5. **Install packages:**
   ```bash
   pip install -r requirements.txt
   ```
   
   This takes 2-3 minutes. Lots of text will scroll by - that's normal!

6. **Create .env file:**
   
   **Mac/Linux:**
   ```bash
   cat > .env << 'EOF'
   SUPABASE_URL=your-url-here
   SUPABASE_KEY=your-key-here
   STORE_ID=your-store-id-here
   EOF
   ```
   
   **Windows:**
   - Open Notepad
   - Paste your actual credentials from credentials.txt
   - Save as `.env` in customer-service folder

✅ Customer service environment ready!

---

## 🚀 PHASE 3: BUILD CUSTOMER SERVICE API (2 hours)

### Step 3.1: Create Basic API (30 minutes)

**What is an API?**
Think of it as a waiter in a restaurant. Frontend asks API for data, API gets it from database.

**Actions:**

1. **Create main.py file:**
   
   **Mac/Linux:**
   ```bash
   touch main.py
   ```
   
   **Windows:**
   - Right-click in customer-service folder
   - New → Text Document
   - Name it `main.py`

2. **Open main.py in a text editor:**
   - Notepad (Windows)
   - TextEdit (Mac)
   - VS Code (if you have it)

3. **Paste this code:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="BazaarOps Customer Service",
    description="Customer-facing service",
    version="1.0.0"
)

# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check - test if service is running
@app.get("/")
async def root():
    return {
        "service": "customer-service",
        "status": "running",
        "message": "Welcome to BazaarOps!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run the app (only when executing this file directly)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

4. **Save the file**

5. **Test it:**
   ```bash
   python main.py
   ```

6. **You should see:**
   ```
   INFO:     Started server process
   INFO:     Uvicorn running on http://0.0.0.0:8002
   ```

7. **Open your browser:**
   - Go to: http://localhost:8002
   - You should see JSON: `{"service": "customer-service", "status": "running"...}`

8. **Press Ctrl+C in Terminal to stop the server**

✅ Basic API works!

---

### Step 3.2: Add Database Service (45 minutes)

**Actions:**

1. **Create folders:**
   ```bash
   mkdir services
   mkdir routers
   mkdir models
   ```

2. **Create __init__.py files** (these make folders into Python packages):
   
   **Mac/Linux:**
   ```bash
   touch services/__init__.py
   touch routers/__init__.py
   touch models/__init__.py
   ```
   
   **Windows:**
   - Create empty files named `__init__.py` in each folder

3. **Create services/db_service.py:**

```python
from supabase import create_client, Client
import os

# Connect to Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class DatabaseService:
    """Handle all database operations"""
    
    @staticmethod
    def get_products(store_id: str):
        """Get all products for a store"""
        try:
            response = supabase.table("inventory")\
                .select("*, products(id, name, description, unit)")\
                .eq("store_id", store_id)\
                .gt("quantity", 0)\
                .execute()
            
            return response.data
        except Exception as e:
            print(f"❌ Error getting products: {e}")
            return []
    
    @staticmethod
    def create_order(store_id: str, customer_id: str, items: list, 
                    total_amount: float, is_credit: bool):
        """Create a new order"""
        try:
            # Create the order
            order_data = {
                "store_id": store_id,
                "customer_id": customer_id,
                "total_amount": total_amount,
                "status": "pending",
                "payment_status": "unpaid" if is_credit else "paid"
            }
            
            order_response = supabase.table("orders")\
                .insert(order_data)\
                .execute()
            
            order_id = order_response.data[0]["id"]
            
            # Create order items
            for item in items:
                item_data = {
                    "order_id": order_id,
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "subtotal": item["quantity"] * item["unit_price"]
                }
                supabase.table("order_items").insert(item_data).execute()
            
            return order_id
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            return None
    
    @staticmethod
    def get_customer_by_phone(store_id: str, phone: str):
        """Find customer by phone or create new one"""
        try:
            # Try to find existing customer
            response = supabase.table("customers")\
                .select("*")\
                .eq("store_id", store_id)\
                .eq("phone", phone)\
                .execute()
            
            if response.data:
                return response.data[0]
            
            # Create new customer if not found
            customer_data = {
                "store_id": store_id,
                "name": f"Customer {phone[-4:]}",
                "phone": phone
            }
            new_response = supabase.table("customers")\
                .insert(customer_data)\
                .execute()
            
            return new_response.data[0]
        except Exception as e:
            print(f"❌ Error with customer: {e}")
            return None

# Create instance to use
db = DatabaseService()
```

4. **Save the file**

✅ Database service created!

---

### Step 3.3: Add API Endpoints (45 minutes)

**Actions:**

1. **Create routers/customer.py:**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from services.db_service import db
import os

router = APIRouter(prefix="/api/customer", tags=["customer"])

# Data models for validation
class OrderItem(BaseModel):
    product_id: str
    product_name: str
    quantity: float
    unit_price: float

class CreateOrderRequest(BaseModel):
    customer_phone: str
    items: List[OrderItem]
    is_credit: bool = False

# Endpoint to get products
@router.get("/products/{store_id}")
async def get_products(store_id: str):
    """
    Get all available products
    
    Try it: http://localhost:8002/api/customer/products/your-store-id
    """
    print(f"📦 Getting products for store: {store_id}")
    
    products = db.get_products(store_id)
    
    # Format the response nicely
    formatted_products = [
        {
            "product_id": item["product_id"],
            "name": item["products"]["name"],
            "description": item["products"]["description"],
            "unit": item["products"]["unit"],
            "price": float(item["unit_price"]),
            "available": float(item["quantity"])
        }
        for item in products
    ]
    
    return {
        "success": True,
        "store_id": store_id,
        "products": formatted_products,
        "count": len(formatted_products)
    }

# Endpoint to place order
@router.post("/order/{store_id}")
async def place_order(store_id: str, order: CreateOrderRequest):
    """
    Place a new order
    
    Send JSON like:
    {
      "customer_phone": "9876543210",
      "items": [
        {
          "product_id": "abc-123",
          "product_name": "Atta",
          "quantity": 2,
          "unit_price": 40
        }
      ],
      "is_credit": false
    }
    """
    print(f"🛒 Placing order for store: {store_id}")
    
    # Get or create customer
    customer = db.get_customer_by_phone(store_id, order.customer_phone)
    if not customer:
        raise HTTPException(status_code=400, detail="Could not create customer")
    
    # Calculate total
    total = sum(item.quantity * item.unit_price for item in order.items)
    
    # Create order
    order_id = db.create_order(
        store_id=store_id,
        customer_id=customer["id"],
        items=[item.dict() for item in order.items],
        total_amount=total,
        is_credit=order.is_credit
    )
    
    if not order_id:
        raise HTTPException(status_code=500, detail="Could not create order")
    
    print(f"✅ Order created: {order_id}")
    
    return {
        "success": True,
        "order_id": order_id,
        "customer_name": customer["name"],
        "total_amount": total,
        "message": "Order placed successfully!"
    }
```

2. **Save the file**

3. **Update main.py to include the router:**
   
   Add these lines near the top (after imports):
   ```python
   from routers import customer
   ```
   
   Add this line after creating the app:
   ```python
   app.include_router(customer.router)
   ```

4. **Your complete main.py should look like:**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import customer  # NEW!
import os

load_dotenv()

app = FastAPI(
    title="BazaarOps Customer Service",
    description="Customer-facing service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include customer routes
app.include_router(customer.router)  # NEW!

@app.get("/")
async def root():
    return {
        "service": "customer-service",
        "status": "running",
        "message": "Welcome to BazaarOps!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

5. **Test the complete API:**
   ```bash
   python main.py
   ```

6. **Open browser:**
   - Go to: http://localhost:8002/docs
   - You'll see Swagger UI (automatic API documentation!)
   - Click on "GET /api/customer/products/{store_id}"
   - Click "Try it out"
   - Enter your STORE_ID
   - Click "Execute"
   - You should see all your products! 🎉

✅ **PHASE 3 COMPLETE!** Customer Service API is working!

---

## 🤖 PHASE 4: TELEGRAM BOT (2 hours)

### Step 4.1: Create Telegram Bot (15 minutes)

**Actions:**

1. **Open Telegram app on your phone**

2. **Search for: @BotFather**
   - This is Telegram's official bot creator

3. **Start chat with BotFather**
   - Tap "Start"

4. **Create your bot:**
   - Type: `/newbot`
   - BotFather asks: "What will be the name?"
   - Reply: `BazaarOps Customer Bot`
   - BotFather asks: "What will be the username?"
   - Reply: `bazaarops_customer_bot` (must end with _bot)

5. **Save your token:**
   - BotFather gives you a token like:
     `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - **COPY THIS!**
   - Add to your credentials.txt:
     ```
     TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
     ```

6. **Test your bot:**
   - Search for your bot username
   - Tap "Start"
   - It should say "Hi!" (default message)

✅ Bot created!

---

### Step 4.2: Build the Bot (1 hour 30 minutes)

**Actions:**

1. **Go to telegram-bots folder:**
   ```bash
   cd ..  # Go back to bazaarops folder
   cd telegram-bots
   mkdir customer-bot
   cd customer-bot
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Mac/Linux
   # OR
   venv\Scripts\activate  # Windows
   ```

3. **Create requirements.txt:**
   ```
   python-telegram-bot==20.7
   python-dotenv==1.0.0
   httpx==0.25.0
   ```

4. **Install packages:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create .env file with your credentials:**
   ```
   TELEGRAM_BOT_TOKEN=your-token-here
   STORE_ID=your-store-id-here
   CUSTOMER_SERVICE_URL=http://localhost:8002
   ```

6. **Create bot.py:**

```python
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

# Configuration
CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL")
STORE_ID = os.getenv("STORE_ID")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message when user starts bot"""
    keyboard = [
        [KeyboardButton("📦 View Products")],
        [KeyboardButton("🛍️ Place Order")],
        [KeyboardButton("📋 My Orders")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🛒 *Welcome to BazaarOps!*\n\n"
        "I'm your personal shopping assistant.\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# View products
async def view_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and show products"""
    await update.message.reply_text("📦 Fetching products...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{STORE_ID}",
                timeout=10.0
            )
            data = response.json()
        
        if not data.get("success"):
            await update.message.reply_text("❌ Could not fetch products")
            return
        
        products = data.get("products", [])
        
        if not products:
            await update.message.reply_text("No products available.")
            return
        
        # Format products nicely
        message = "📦 *Available Products:*\n\n"
        for i, product in enumerate(products, 1):
            message += f"{i}. *{product['name']}*\n"
            message += f"   ₹{product['price']}/{product['unit']}\n"
            message += f"   Available: {product['available']} {product['unit']}\n"
            if product.get('description'):
                message += f"   _{product['description']}_\n"
            message += "\n"
        
        message += "💡 To order, type:\n`order <product> <quantity>`\n\n"
        message += "Example: `order Atta 2`"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error fetching products. Try again!")

# Process order
async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process order from text"""
    try:
        # Parse "order Atta 2"
        parts = update.message.text.split()
        
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Format: `order <product> <quantity>`\n"
                "Example: `order Atta 2`",
                parse_mode='Markdown'
            )
            return
        
        # Extract product name and quantity
        product_name = " ".join(parts[1:-1])
        quantity = float(parts[-1])
        
        # Use Telegram user ID as phone
        customer_phone = str(update.effective_user.id)
        
        await update.message.reply_text(
            f"🔄 Processing order for {quantity} {product_name}..."
        )
        
        # Get products first
        async with httpx.AsyncClient() as client:
            products_response = await client.get(
                f"{CUSTOMER_SERVICE_URL}/api/customer/products/{STORE_ID}"
            )
            products_data = products_response.json()
        
        # Find matching product
        matching_product = None
        for product in products_data.get("products", []):
            if product_name.lower() in product["name"].lower():
                matching_product = product
                break
        
        if not matching_product:
            await update.message.reply_text(
                f"❌ '{product_name}' not found.\n"
                "Type 'view products' to see what's available."
            )
            return
        
        # Check availability
        if quantity > matching_product["available"]:
            await update.message.reply_text(
                f"❌ Only {matching_product['available']} "
                f"{matching_product['unit']} available."
            )
            return
        
        # Place order
        order_data = {
            "customer_phone": customer_phone,
            "items": [
                {
                    "product_id": matching_product["product_id"],
                    "product_name": matching_product["name"],
                    "quantity": quantity,
                    "unit_price": matching_product["price"]
                }
            ],
            "is_credit": False
        }
        
        async with httpx.AsyncClient() as client:
            order_response = await client.post(
                f"{CUSTOMER_SERVICE_URL}/api/customer/order/{STORE_ID}",
                json=order_data,
                timeout=10.0
            )
            order_result = order_response.json()
        
        if order_result.get("success"):
            total = quantity * matching_product["price"]
            await update.message.reply_text(
                f"✅ *Order Placed!*\n\n"
                f"Product: {matching_product['name']}\n"
                f"Quantity: {quantity} {matching_product['unit']}\n"
                f"Price: ₹{matching_product['price']}/{matching_product['unit']}\n"
                f"*Total: ₹{total}*\n\n"
                f"Order ID: `{order_result['order_id'][:8]}...`\n\n"
                f"Store will confirm soon!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Could not place order. Try again!")
    
    except ValueError:
        await update.message.reply_text("❌ Invalid quantity. Use a number.")
    except Exception as e:
        print(f"❌ Error: {e}")
        await update.message.reply_text("❌ Error processing order. Try again!")

# Handle all text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route messages to correct handler"""
    text = update.message.text.lower()
    
    if "view products" in text or "📦" in text:
        await view_products(update, context)
    
    elif "place order" in text or "🛍️" in text:
        await update.message.reply_text(
            "📝 To place order:\n`order <product> <quantity>`\n\n"
            "Example: `order Atta 2`",
            parse_mode='Markdown'
        )
    
    elif text.startswith("order "):
        await process_order(update, context)
    
    else:
        await update.message.reply_text(
            "Try:\n"
            "• 📦 View Products\n"
            "• Type: order <product> <quantity>"
        )

# Main function
def main():
    """Start the bot"""
    print("🤖 Starting Customer Bot...")
    print(f"Store ID: {STORE_ID}")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    print("✅ Bot is running!")
    print("Press Ctrl+C to stop")
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```

7. **Save the file**

✅ Bot code ready!

---

### Step 4.3: Test Complete Flow (15 minutes)

**You need 2 Terminal windows:**

**Terminal 1 - Customer Service:**
```bash
cd bazaarops/customer-service
source venv/bin/activate
python main.py
```

**Terminal 2 - Telegram Bot:**
```bash
cd bazaarops/telegram-bots/customer-bot
source venv/bin/activate
python bot.py
```

**Both should be running!**

**Now test on Telegram:**

1. Open Telegram app
2. Find your bot
3. Send: `/start`
4. Tap: "📦 View Products"
5. You should see your products!
6. Type: `order Atta 2`
7. You should see: "✅ Order Placed!"

**Verify in Supabase:**
1. Go to Supabase dashboard
2. Click "Table Editor"
3. Click "orders" table
4. You should see a new order!
5. Click "inventory" table
6. Atta quantity should be reduced!

✅ **PHASE 4 COMPLETE!** Bot works end-to-end!

---

## 🧠 PHASE 5: AGENT SERVICE WITH CLAUDE SDK (2.5 hours)

### Step 5.1: Get Anthropic API Key (10 minutes)

**Actions:**

1. **Go to:** https://console.anthropic.com
2. **Sign up / Log in**
3. **Click "API Keys"** in left menu
4. **Click "Create Key"**
5. **Copy the key** (starts with `sk-ant-api...`)
6. **Add to credentials.txt:**
   ```
   ANTHROPIC_API_KEY=sk-ant-api-your-key-here
   ```

✅ API key obtained!

---

### Step 5.2: Install Claude Agent SDK (15 minutes)

**Actions:**

1. **Go to agent-service folder:**
   ```bash
   cd ../..  # Back to bazaarops
   cd agent-service
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate
   ```

3. **Create requirements.txt:**
   ```
   fastapi==0.104.1
   uvicorn==0.24.0
   claude-agent-sdk==0.1.5
   supabase==2.0.3
   python-dotenv==1.0.0
   httpx==0.25.0
   ```

4. **Install:**
   ```bash
   pip install -r requirements.txt
   ```
   
   This takes 3-5 minutes.

5. **Create .env file:**
   ```
   SUPABASE_URL=your-url
   SUPABASE_KEY=your-key
   STORE_ID=your-store-id
   ANTHROPIC_API_KEY=sk-ant-api-your-key
   ```

✅ Claude Agent SDK installed!

---

### Step 5.3: Create Event System (20 minutes)

**Actions:**

1. **Create folders:**
   ```bash
   mkdir events
   mkdir agents
   touch events/__init__.py
   touch agents/__init__.py
   ```

2. **Create events/event_bus.py:**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Callable

@dataclass
class Event:
    """An event that triggers agents"""
    type: str
    store_id: str
    payload: Dict
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EventBus:
    """Manages events and notifies agents"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        """Agent subscribes to an event"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        print(f"📡 Subscribed to: {event_type}")
    
    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        print(f"🔔 Event: {event.type} for store {event.store_id}")
        
        if event.type in self.handlers:
            for handler in self.handlers[event.type]:
                try:
                    await handler(event)
                except Exception as e:
                    print(f"❌ Handler error: {e}")

# Global instance
event_bus = EventBus()
```

✅ Event system created!

---

### Step 5.4: Create Order Agent (30 minutes)

**Actions:**

1. **Create agents/order_agent.py:**

```python
from events.event_bus import event_bus, Event
from supabase import create_client
import os

class OrderAgent:
    """Processes orders automatically"""
    
    def __init__(self):
        # Connect to database
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Subscribe to order events
        event_bus.subscribe("order_created", self.handle_order)
        print("✅ Order Agent ready")
    
    async def handle_order(self, event: Event):
        """Process an order"""
        print(f"🛒 Processing order...")
        
        try:
            payload = event.payload
            order_id = payload.get("order_id")
            items = payload.get("items", [])
            
            # Update inventory for each item
            for item in items:
                await self.update_inventory(
                    event.store_id,
                    item["product_id"],
                    item["quantity"]
                )
            
            # Mark order as confirmed
            self.supabase.table("orders")\
                .update({"status": "confirmed"})\
                .eq("id", order_id)\
                .execute()
            
            print(f"✅ Order {order_id[:8]} confirmed")
            
            # Trigger inventory check
            await event_bus.publish(Event(
                type="inventory_updated",
                store_id=event.store_id,
                payload={"order_id": order_id}
            ))
            
        except Exception as e:
            print(f"❌ Order error: {e}")
    
    async def update_inventory(self, store_id: str, 
                             product_id: str, quantity: float):
        """Reduce inventory"""
        # Get current stock
        response = self.supabase.table("inventory")\
            .select("quantity")\
            .eq("store_id", store_id)\
            .eq("product_id", product_id)\
            .execute()
        
        if response.data:
            current = float(response.data[0]["quantity"])
            new = current - quantity
            
            # Update
            self.supabase.table("inventory")\
                .update({"quantity": new})\
                .eq("store_id", store_id)\
                .eq("product_id", product_id)\
                .execute()
            
            print(f"📦 Stock updated: {current} → {new}")
```

✅ Order Agent created!

---

### Step 5.5: Create Summary Agent with Claude SDK (45 minutes)

**Actions:**

1. **Create agents/summary_agent.py:**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from events.event_bus import event_bus, Event
from supabase import create_client
from datetime import datetime
import os

class SummaryAgent:
    """Generates daily summaries with AI"""
    
    def __init__(self):
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        event_bus.subscribe("generate_daily_summary", self.handle_summary)
        print("✅ Summary Agent ready (with Claude SDK)")
    
    async def handle_summary(self, event: Event):
        """Generate AI summary"""
        print(f"📊 Generating summary...")
        
        try:
            # Get today's data
            data = await self.get_daily_data(event.store_id)
            
            # Create prompt for Claude
            prompt = f"""You are a business analyst for a kirana store.

Today's Performance:
- Revenue: ₹{data['revenue']}
- Orders: {data['orders']}
- Top Products: {', '.join(data['top_products'])}
- Low Stock: {', '.join(data['low_stock'])}

Generate a brief summary in Hinglish (Hindi-English mix) that:
1. Highlights key wins
2. Points out concerns
3. Gives 2-3 actionable tips

Keep it friendly and practical."""

            # Use Claude Agent SDK
            summary = ""
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    model="claude-sonnet-4-20250514",
                    max_tokens=500
                )
            ):
                if hasattr(message, 'text'):
                    summary += message.text
            
            print(f"✅ Summary generated!")
            print(f"\n{summary}\n")
            
            # In real app, send to owner via Telegram
            
        except Exception as e:
            print(f"❌ Summary error: {e}")
    
    async def get_daily_data(self, store_id: str):
        """Collect today's stats"""
        today = datetime.now().date()
        
        # Get orders
        orders = self.supabase.table("orders")\
            .select("total_amount")\
            .eq("store_id", store_id)\
            .gte("created_at", today.isoformat())\
            .execute()
        
        revenue = sum(float(o["total_amount"]) for o in orders.data)
        count = len(orders.data)
        
        # Get low stock
        inventory = self.supabase.table("inventory")\
            .select("*, products(name)")\
            .eq("store_id", store_id)\
            .execute()
        
        low_stock = [
            item["products"]["name"]
            for item in inventory.data
            if item["quantity"] < item["reorder_threshold"]
        ]
        
        return {
            "revenue": revenue,
            "orders": count,
            "top_products": ["Atta", "Rice", "Sugar"],
            "low_stock": low_stock if low_stock else ["None"]
        }
```

✅ Summary Agent with Claude SDK created!

---

### Step 5.6: Create Main Service (30 minutes)

**Actions:**

1. **Create main.py:**

```python
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from events.event_bus import Event, event_bus
from agents.order_agent import OrderAgent
from agents.summary_agent import SummaryAgent
from dotenv import load_dotenv

load_dotenv()

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

@app.post("/api/events/trigger")
async def trigger_event(
    event_type: str,
    store_id: str,
    payload: dict,
    background_tasks: BackgroundTasks
):
    """Trigger an event"""
    event = Event(
        type=event_type,
        store_id=store_id,
        payload=payload
    )
    
    background_tasks.add_task(event_bus.publish, event)
    
    return {
        "success": True,
        "event_type": event_type,
        "message": "Event triggered"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "sdk": "claude-agent-sdk"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
```

2. **Save and run:**
   ```bash
   python main.py
   ```

3. **You should see:**
   ```
   🤖 Initializing agents...
   📡 Subscribed to: order_created
   ✅ Order Agent ready
   📡 Subscribed to: generate_daily_summary
   ✅ Summary Agent ready (with Claude SDK)
   ✅ All agents ready!
   INFO:     Uvicorn running on http://0.0.0.0:8003
   ```

✅ **PHASE 5 COMPLETE!** Agent service running!

---

## 🔗 PHASE 6: CONNECT EVERYTHING (30 minutes)

### Step 6.1: Connect Customer Service to Agent Service

**Actions:**

1. **Open customer-service/routers/customer.py**

2. **Add this import at top:**
   ```python
   import httpx
   ```

3. **Find the `place_order` function**

4. **Add this code AFTER the line `if not order_id:`:**

```python
    # Trigger agent service
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8003/api/events/trigger",
                json={
                    "event_type": "order_created",
                    "store_id": store_id,
                    "payload": {
                        "order_id": order_id,
                        "customer_id": customer["id"],
                        "items": [item.dict() for item in order.items],
                        "is_credit": order.is_credit
                    }
                },
                timeout=5.0
            )
            print("✅ Agent notified")
    except Exception as e:
        print(f"⚠️ Could not notify agent: {e}")
```

5. **Save the file**

✅ Services connected!

---

### Step 6.2: Test Complete System

**You need 3 Terminal windows:**

**Terminal 1 - Customer Service:**
```bash
cd bazaarops/customer-service
source venv/bin/activate
python main.py
```

**Terminal 2 - Agent Service:**
```bash
cd bazaarops/agent-service
source venv/bin/activate
python main.py
```

**Terminal 3 - Telegram Bot:**
```bash
cd bazaarops/telegram-bots/customer-bot
source venv/bin/activate
python bot.py
```

**All 3 running? Now test!**

**On Telegram:**
1. Open your bot
2. Send: `/start`
3. Type: `order Atta 2`

**Watch the terminals:**
- Terminal 1 (Customer Service): Should show "Order created"
- Terminal 2 (Agent Service): Should show "Processing order", "Stock updated", "Order confirmed"
- Terminal 3 (Bot): Should show "Order placed"

**Check Supabase:**
- Orders table: New order with status "confirmed"
- Inventory table: Atta quantity reduced by 2

**If all this works - YOU DID IT! 🎉🎉🎉**

---

## 🎯 PHASE 7: TEST CLAUDE SDK (15 minutes)

### Test Summary Agent

**In browser, open:**
```
http://localhost:8003/api/events/trigger?event_type=generate_daily_summary&store_id=YOUR_STORE_ID&payload={}
```

**Watch Terminal 2:**
You should see Claude generate a summary in Hinglish!

Example output:
```
📊 Generating summary...
✅ Summary generated!

Aaj ka din accha raha! 

Revenue: ₹280 with 2 orders - great start! 
Top sellers: Atta, Rice, Sugar - staples always sell well.

⚠️ Concern: Atta stock is low (8kg remaining)

Tips:
1. Reorder Atta today - popular item!
2. Consider combo offers: Atta + Dal
3. Track evening rush for better stock planning

Keep it up! 🎉
```

✅ Claude SDK working!

---

## ✅ FINAL CHECKLIST

### Phase 1: Database
- [ ] Supabase account created
- [ ] 9 tables created
- [ ] RLS enabled
- [ ] Sample data inserted
- [ ] Credentials saved

### Phase 2: Python Setup
- [ ] Python installed
- [ ] Project folders created
- [ ] Virtual environments working
- [ ] Packages installed

### Phase 3: Customer Service
- [ ] API running on port 8002
- [ ] GET /products works
- [ ] POST /order works
- [ ] Can access /docs

### Phase 4: Telegram Bot
- [ ] Bot created
- [ ] Bot responds to /start
- [ ] Can view products
- [ ] Can place orders

### Phase 5: Agent Service
- [ ] Running on port 8003
- [ ] Order Agent works
- [ ] Summary Agent works
- [ ] Claude SDK responds

### Phase 6: Integration
- [ ] All 3 services running together
- [ ] Bot order → Customer Service → Agent Service
- [ ] Inventory updates automatically
- [ ] Orders marked as confirmed

### Phase 7: AI Features
- [ ] Claude SDK generates summaries
- [ ] Responses in Hinglish
- [ ] Quality output

---

## 🎬 DEMO PREPARATION

### Your Demo Script (2-3 minutes)

**Minute 1: Architecture**
"We built a microservice architecture with 3 services:
- Customer Service (Port 8002)
- Agent Service with Claude SDK (Port 8003)
- Telegram Bot

All connected via events."

**Minute 2: Live Demo**
1. Show Telegram bot
2. Place order: "order Atta 2"
3. Show terminals - watch agents process
4. Show Supabase - order confirmed, inventory updated

**Minute 3: AI Feature**
1. Trigger summary agent
2. Show Claude SDK generate Hinglish summary
3. Explain: "Same tech as Claude Code"

---

## 🚨 TROUBLESHOOTING

### "Module not found"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall
pip install -r requirements.txt
```

### "Connection refused"
```bash
# Check if service is running
curl http://localhost:8002
curl http://localhost:8003

# Check what's using the port
lsof -i :8002  # Mac
netstat -ano | findstr :8002  # Windows
```

### "Supabase error"
- Check .env has correct credentials
- Check internet connection
- Verify STORE_ID is correct

### Bot not responding
- Check TELEGRAM_BOT_TOKEN in .env
- Make sure bot.py is running
- Check customer service is running

### Claude SDK not working
- Check ANTHROPIC_API_KEY in .env
- Check you have API credits
- Try a simple query first

---

## 🏆 YOU'RE DONE!

You've built:
- ✅ Multi-tenant database (9 tables)
- ✅ Customer Service API (REST)
- ✅ Telegram Bot (customer interface)
- ✅ Event-driven Agent Service
- ✅ AI Agents with Claude SDK
- ✅ Complete order processing flow

**Now coordinate with Dev 1 for final integration! 🚀**

Share with Dev 1:
1. credentials.txt
2. Your API endpoints (port 8002)
3. Agent service endpoint (port 8003)
4. How to trigger events

**Good luck at the hackathon! 💪**

# Advanced Agentic Features - Design Document

## 1. Architecture Overview

### 1.1 System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Event-Driven Core                        │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐      │
│  │  Redis   │◄───┤  Event   │◄───┤   PostgreSQL     │      │
│  │ Pub/Sub  │    │   Bus    │    │    Triggers      │      │
│  └────┬─────┘    └──────────┘    └──────────────────┘      │
└───────┼──────────────────────────────────────────────────────┘
        │
        ├──► Agent Service (Orchestrator)
        │    ├─► Inventory Agent
        │    ├─► Customer Lifecycle Agent
        │    ├─► Credit Collection Agent
        │    ├─► BI Agent
        │    ├─► Fraud Detection Agent
        │    ├─► Notification Orchestrator
        │    └─► Coordinator Agent
        │
        ├──► Owner Service (API)
        ├──► Customer Service (API)
        ├──► Owner Bot (Telegram)
        └──► Customer Bot (Telegram)
```

### 1.2 Data Flow
```
Customer places order
  → Customer Service API
  → Database INSERT (order)
  → PostgreSQL Trigger fires
  → Event published to Redis
  → Multiple agents subscribe:
     - Inventory Agent (reduce stock)
     - Fraud Agent (check risk)
     - Notification Agent (notify owner)
     - BI Agent (update metrics)
  → Agents process in parallel
  → Results stored in database
  → Owner/Customer notified
```

## 2. Component Design

### 2.1 Event-Driven Architecture

#### Event Types
```python
class EventType(Enum):
    ORDER_CREATED = "order.created"
    ORDER_UPDATED = "order.updated"
    ORDER_COMPLETED = "order.completed"
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_OVERDUE = "payment.overdue"
    INVENTORY_LOW = "inventory.low"
    INVENTORY_CRITICAL = "inventory.critical"
    CUSTOMER_INACTIVE = "customer.inactive"
    CUSTOMER_CHURN_RISK = "customer.churn_risk"
    PRODUCT_TRENDING = "product.trending"
    FRAUD_DETECTED = "fraud.detected"
```

#### Event Structure
```python
{
    "event_id": "uuid",
    "event_type": "order.created",
    "timestamp": "2026-02-15T10:30:00Z",
    "store_id": "store-uuid",
    "data": {
        "order_id": "order-uuid",
        "customer_id": "customer-uuid",
        "total_amount": 500.00,
        "items": [...]
    },
    "metadata": {
        "source": "customer-service",
        "version": "1.0"
    }
}
```

#### Event Bus Implementation
- **Publisher:** FastAPI services publish events after DB operations
- **Broker:** Redis Pub/Sub for real-time distribution
- **Subscribers:** Agent service subscribes to relevant events
- **Dead Letter Queue:** Failed events stored for retry
- **Event Log:** All events logged in PostgreSQL for audit

### 2.2 Autonomous Inventory Orchestrator

#### Components
1. **Demand Forecasting Engine**
   - Input: Historical sales data (30/60/90 days)
   - Algorithm: Moving average + trend analysis
   - Output: Predicted demand for next 7-14 days
   - Confidence score: 0-100%

2. **Reorder Decision Engine**
   - Input: Current stock, forecast, reorder threshold
   - Logic:
     ```python
     days_until_stockout = current_stock / avg_daily_sales
     if days_until_stockout < 7:
         suggested_quantity = (forecast_14_days - current_stock) * 1.2  # 20% buffer
         send_approval_request()
     ```

3. **Owner Approval System**
   - Telegram inline keyboard with buttons
   - Approval data stored in `reorder_approvals` table
   - Learning: Track owner's edits to improve suggestions

4. **Supplier Communication**
   - WhatsApp message generation
   - Template: "Hi {supplier}, please send {quantity} {unit} of {product}. Expected delivery: {date}"
   - Tracking: Store in `pending_supplier_orders` table

#### Database Schema
```sql
CREATE TABLE pending_supplier_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID REFERENCES stores(id),
    product_id UUID REFERENCES products(id),
    quantity DECIMAL NOT NULL,
    suggested_by_agent BOOLEAN DEFAULT TRUE,
    owner_approved BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMP,
    supplier_contacted BOOLEAN DEFAULT FALSE,
    expected_delivery_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reorder_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reorder_id UUID REFERENCES pending_supplier_orders(id),
    suggested_quantity DECIMAL,
    approved_quantity DECIMAL,
    owner_edited BOOLEAN DEFAULT FALSE,
    edit_percentage DECIMAL,  -- For learning
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.3 Intelligent Customer Lifecycle Manager

#### VIP Detection Algorithm
```python
def calculate_vip_status(customer):
    # Calculate Customer Lifetime Value
    total_spent = sum(order.total_amount for order in customer.orders)
    order_count = len(customer.orders)
    avg_order_value = total_spent / order_count if order_count > 0 else 0
    
    # Calculate frequency score
    if order_count > 0:
        days_active = (datetime.now() - customer.first_order_date).days
        order_frequency = order_count / (days_active / 30)  # Orders per month
    else:
        order_frequency = 0
    
    # VIP criteria
    is_vip = (
        total_spent > 10000 OR  # Spent more than ₹10k
        order_count > 20 OR     # More than 20 orders
        order_frequency > 4     # Orders 4+ times per month
    )
    
    return is_vip
```

#### Birthday Wishes System
```python
# Daily cron job at 9 AM
def send_birthday_wishes():
    today = datetime.now().strftime("%m-%d")
    customers = db.query(Customer).filter(
        Customer.birthday == today,
        Customer.is_vip == True
    ).all()
    
    for customer in customers:
        message = generate_birthday_message(customer)  # AI-generated
        send_telegram_message(customer.telegram_chat_id, message)
        log_birthday_wish(customer.id)
```

#### Churn Prediction
```python
def detect_churn_risk(customer):
    if not customer.last_order_date:
        return False
    
    days_since_last_order = (datetime.now() - customer.last_order_date).days
    
    # Calculate average order interval
    order_dates = [order.created_at for order in customer.orders]
    if len(order_dates) < 2:
        avg_interval = 30  # Default
    else:
        intervals = [(order_dates[i] - order_dates[i-1]).days 
                     for i in range(1, len(order_dates))]
        avg_interval = sum(intervals) / len(intervals)
    
    # Churn risk if current gap > 2x average
    is_at_risk = days_since_last_order > (avg_interval * 2)
    risk_level = "high" if days_since_last_order > 30 else "medium"
    
    return is_at_risk, risk_level
```

#### Database Schema
```sql
ALTER TABLE customers ADD COLUMN birthday VARCHAR(5);  -- MM-DD format
ALTER TABLE customers ADD COLUMN is_vip BOOLEAN DEFAULT FALSE;
ALTER TABLE customers ADD COLUMN last_order_date TIMESTAMP;
ALTER TABLE customers ADD COLUMN avg_order_interval INTEGER;  -- Days
ALTER TABLE customers ADD COLUMN churn_risk_level VARCHAR(20);

CREATE TABLE customer_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    segment_type VARCHAR(50),  -- 'vip', 'at_risk', 'dormant', 'new'
    assigned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE birthday_wishes_sent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    sent_at TIMESTAMP DEFAULT NOW(),
    message_text TEXT,
    responded BOOLEAN DEFAULT FALSE
);
```

### 2.4 Predictive Credit & Collection System

#### Credit Scoring Algorithm
```python
def calculate_credit_score(customer):
    base_score = 50
    
    # Payment history (max +30 or -30)
    payment_history = get_payment_history(customer.id)
    on_time_payments = sum(1 for p in payment_history if p.days_to_payment <= 7)
    late_payments = sum(1 for p in payment_history if p.days_to_payment > 7)
    total_payments = len(payment_history)
    
    if total_payments > 0:
        payment_score = ((on_time_payments - late_payments) / total_payments) * 30
    else:
        payment_score = 0
    
    # Order frequency (max +10)
    order_count = len(customer.orders)
    frequency_score = min(order_count / 2, 10)  # 1 point per 2 orders, max 10
    
    # Total spent (max +10)
    total_spent = sum(order.total_amount for order in customer.orders)
    spending_score = min(total_spent / 1000, 10)  # 1 point per ₹1000, max 10
    
    final_score = base_score + payment_score + frequency_score + spending_score
    return max(0, min(100, final_score))  # Clamp between 0-100
```

#### Credit Limit Calculation
```python
def calculate_credit_limit(credit_score):
    if credit_score >= 70:
        return 5000
    elif credit_score >= 50:
        return 2000
    else:
        return 0  # Cash only
```

#### Collection Strategy
```python
def get_collection_strategy(days_overdue, payment_history_score):
    if days_overdue <= 3:
        return {
            "tone": "friendly",
            "message": "Hi! Just a gentle reminder about your pending payment of ₹{amount} 😊",
            "urgency": "low"
        }
    elif days_overdue <= 7:
        return {
            "tone": "neutral",
            "message": "Payment of ₹{amount} pending for {days} days. Please pay soon.",
            "urgency": "medium"
        }
    elif days_overdue <= 15:
        return {
            "tone": "firm",
            "message": "⚠️ Payment of ₹{amount} overdue by {days} days. Please clear immediately.",
            "urgency": "high"
        }
    else:  # 30+ days
        return {
            "tone": "strict",
            "message": "🚨 URGENT: Payment of ₹{amount} overdue by {days} days. Credit suspended until payment received.",
            "urgency": "critical",
            "action": "suspend_credit"
        }
```

#### Database Schema
```sql
ALTER TABLE customers ADD COLUMN credit_score INTEGER DEFAULT 50;
ALTER TABLE customers ADD COLUMN credit_limit DECIMAL DEFAULT 0;
ALTER TABLE customers ADD COLUMN credit_suspended BOOLEAN DEFAULT FALSE;

CREATE TABLE payment_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    order_id UUID REFERENCES orders(id),
    amount DECIMAL NOT NULL,
    due_date DATE,
    paid_date DATE,
    days_to_payment INTEGER,
    was_late BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE payment_reminders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    order_id UUID REFERENCES orders(id),
    reminder_type VARCHAR(50),  -- 'friendly', 'firm', 'urgent'
    sent_at TIMESTAMP DEFAULT NOW(),
    responded BOOLEAN DEFAULT FALSE,
    payment_received BOOLEAN DEFAULT FALSE
);
```

### 2.5 Conversational AI Shopping Assistant

#### NLP Pipeline
```
User Input: "I need 2kg rice and 1kg sugar"
    ↓
1. Intent Detection (Claude API)
   → Intent: place_order
    ↓
2. Entity Extraction
   → Entities: [
       {product: "rice", quantity: 2, unit: "kg"},
       {product: "sugar", quantity: 1, unit: "kg"}
     ]
    ↓
3. Product Matching (Fuzzy)
   → rice → "Basmati Rice" (score: 0.95)
   → sugar → "White Sugar" (score: 1.0)
    ↓
4. Ambiguity Resolution
   → Multiple rice products found
   → Ask: "Which rice? 1) Basmati ₹80/kg 2) Regular ₹50/kg"
    ↓
5. Order Confirmation
   → Show: "2kg Basmati Rice (₹160) + 1kg Sugar (₹50) = ₹210. Confirm?"
    ↓
6. Place Order
```

#### Implementation
```python
class ConversationalOrderParser:
    def __init__(self):
        self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    async def parse_order(self, user_message, context):
        # Use Claude to extract intent and entities
        prompt = f"""
        Parse this customer order message and extract products, quantities, and units.
        
        Message: "{user_message}"
        
        Return JSON:
        {{
            "intent": "place_order" | "ask_question" | "check_status",
            "items": [
                {{"product": "rice", "quantity": 2, "unit": "kg"}},
                ...
            ]
        }}
        """
        
        response = self.claude_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        parsed = json.loads(response.content[0].text)
        return parsed
    
    async def match_products(self, parsed_items, store_id):
        # Fuzzy matching against store's products
        products = get_store_products(store_id)
        matched = []
        
        for item in parsed_items:
            best_match = None
            best_score = 0
            
            for product in products:
                score = fuzz.ratio(item['product'].lower(), product.name.lower())
                if score > best_score:
                    best_score = score
                    best_match = product
            
            if best_score > 70:  # Threshold
                matched.append({
                    "item": item,
                    "product": best_match,
                    "confidence": best_score
                })
            else:
                matched.append({
                    "item": item,
                    "product": None,
                    "error": "not_found"
                })
        
        return matched
```

#### Context Management
```python
# Store conversation context in Redis
context_key = f"conversation:{user_id}"
context = {
    "last_messages": [],  # Last 5 messages
    "current_cart": [],   # Items being added
    "state": "browsing",  # browsing, ordering, confirming
    "last_products_viewed": []
}
redis.setex(context_key, 3600, json.dumps(context))  # 1 hour TTL
```

#### Database Schema
```sql
CREATE TABLE conversation_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES customers(id),
    session_id VARCHAR(100),
    messages JSONB,  -- Array of messages
    current_cart JSONB,  -- Items in cart
    state VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
```

### 2.6 Business Intelligence System

#### Metrics Calculation
```python
class BIAgent:
    def calculate_trends(self, store_id):
        # Week-over-week comparison
        this_week = get_orders(store_id, days=7)
        last_week = get_orders(store_id, days=14, offset=7)
        
        this_week_revenue = sum(o.total_amount for o in this_week)
        last_week_revenue = sum(o.total_amount for o in last_week)
        
        change_pct = ((this_week_revenue - last_week_revenue) / last_week_revenue) * 100
        
        return {
            "this_week_revenue": this_week_revenue,
            "last_week_revenue": last_week_revenue,
            "change_percentage": change_pct,
            "trend": "up" if change_pct > 0 else "down"
        }
    
    def detect_anomalies(self, store_id):
        # Get average daily orders for last 30 days
        orders_30d = get_orders(store_id, days=30)
        avg_daily_orders = len(orders_30d) / 30
        
        # Get today's orders
        today_orders = get_orders(store_id, days=1)
        today_count = len(today_orders)
        
        # Anomaly if >50% deviation
        if today_count < (avg_daily_orders * 0.5):
            return {
                "type": "low_orders",
                "severity": "high",
                "message": f"Orders down 50%+ today ({today_count} vs avg {avg_daily_orders:.0f})"
            }
        
        return None
    
    def forecast_revenue(self, store_id):
        # Simple linear regression on last 30 days
        orders = get_orders(store_id, days=30)
        daily_revenue = {}
        
        for order in orders:
            date = order.created_at.date()
            daily_revenue[date] = daily_revenue.get(date, 0) + order.total_amount
        
        # Calculate trend
        days = sorted(daily_revenue.keys())
        revenues = [daily_revenue[d] for d in days]
        
        # Linear regression
        slope, intercept = np.polyfit(range(len(revenues)), revenues, 1)
        
        # Forecast next 7 days
        forecast = []
        for i in range(7):
            predicted = slope * (len(revenues) + i) + intercept
            forecast.append(predicted)
        
        return {
            "next_7_days": sum(forecast),
            "daily_forecast": forecast,
            "confidence": "medium"  # Based on R² score
        }
```

### 2.7 Multi-Agent Collaboration

#### Message Bus Protocol
```python
class AgentMessage:
    def __init__(self, from_agent, to_agent, message_type, data, priority):
        self.id = str(uuid.uuid4())
        self.from_agent = from_agent
        self.to_agent = to_agent  # or "broadcast"
        self.message_type = message_type
        self.data = data
        self.priority = priority  # 1-10
        self.timestamp = datetime.now()
    
    def to_dict(self):
        return {
            "id": self.id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type,
            "data": self.data,
            "priority": self.priority,
            "timestamp": self.timestamp.isoformat()
        }

# Example: Low stock scenario
inventory_agent.send_message(
    to_agent="broadcast",
    message_type="inventory.low",
    data={"product_id": "rice-123", "current_stock": 5, "threshold": 10},
    priority=8
)

# Demand agent responds
demand_agent.send_message(
    to_agent="reorder_agent",
    message_type="demand.forecast",
    data={"product_id": "rice-123", "predicted_demand": 50, "confidence": 0.85},
    priority=8
)

# Reorder agent decides
reorder_agent.send_message(
    to_agent="notification_agent",
    message_type="reorder.approval_needed",
    data={"product_id": "rice-123", "suggested_quantity": 100},
    priority=9
)
```

#### Coordinator Agent
```python
class CoordinatorAgent:
    def resolve_conflict(self, messages):
        # Example: Pricing vs Marketing conflict
        # Pricing wants to increase price, Marketing wants discount
        
        # Check owner's current goal
        goal = get_owner_goal(store_id)
        
        if goal == "maximize_profit":
            # Prioritize pricing agent
            return messages["pricing_agent"]
        elif goal == "increase_customers":
            # Prioritize marketing agent
            return messages["marketing_agent"]
        else:
            # Default: Balance both
            return self.find_middle_ground(messages)
```

### 2.8 Smart Notification Orchestrator

#### Timing Optimization
```python
class NotificationOrchestrator:
    def get_optimal_time(self, customer_id):
        # Analyze past response times
        responses = get_notification_responses(customer_id)
        
        if not responses:
            return "18:00"  # Default: 6 PM
        
        # Group by hour
        response_by_hour = {}
        for response in responses:
            hour = response.sent_at.hour
            if response.responded:
                response_by_hour[hour] = response_by_hour.get(hour, 0) + 1
        
        # Find hour with most responses
        best_hour = max(response_by_hour, key=response_by_hour.get)
        return f"{best_hour:02d}:00"
    
    def batch_notifications(self, customer_id):
        # Get pending notifications
        pending = get_pending_notifications(customer_id)
        
        if len(pending) == 0:
            return None
        
        # Combine into one message
        combined = self.combine_messages(pending)
        
        # Schedule at optimal time
        optimal_time = self.get_optimal_time(customer_id)
        schedule_notification(customer_id, combined, optimal_time)
        
        # Mark as batched
        mark_notifications_batched(pending)
```

### 2.9 Fraud Detection System

#### Risk Scoring
```python
def calculate_fraud_risk(order, customer):
    risk_score = 0
    flags = []
    
    # New customer with large order
    if customer.order_count == 0 and order.total_amount > 2000:
        risk_score += 30
        flags.append("new_customer_large_order")
    
    # Order value much higher than average
    if customer.avg_order_value > 0:
        if order.total_amount > (customer.avg_order_value * 5):
            risk_score += 25
            flags.append("unusually_large_order")
    
    # Multiple orders in short time
    recent_orders = get_orders_last_hour(customer.id)
    if len(recent_orders) > 3:
        risk_score += 20
        flags.append("multiple_orders_short_time")
    
    # Credit request from low-score customer
    if order.is_credit and customer.credit_score < 40:
        risk_score += 25
        flags.append("credit_request_low_score")
    
    return {
        "risk_score": risk_score,
        "risk_level": "high" if risk_score > 80 else "medium" if risk_score > 50 else "low",
        "flags": flags
    }
```

## 3. API Endpoints

### 3.1 New Endpoints

```python
# Reorder Management
POST   /api/owner/reorder/approve/{reorder_id}
POST   /api/owner/reorder/reject/{reorder_id}
PUT    /api/owner/reorder/edit/{reorder_id}
GET    /api/owner/reorder/pending/{store_id}

# Customer Lifecycle
GET    /api/owner/customers/vip/{store_id}
GET    /api/owner/customers/at-risk/{store_id}
POST   /api/owner/customers/send-birthday-wishes

# Credit Management
GET    /api/owner/credit/score/{customer_id}
POST   /api/owner/credit/update-limit/{customer_id}
GET    /api/owner/credit/payment-history/{customer_id}

# Business Intelligence
GET    /api/owner/analytics/trends/{store_id}
GET    /api/owner/analytics/forecast/{store_id}
GET    /api/owner/analytics/anomalies/{store_id}

# Fraud Detection
GET    /api/owner/fraud/alerts/{store_id}
POST   /api/owner/fraud/review/{order_id}
```

## 4. Database Migrations

See individual component sections for detailed schema changes.

## 5. Testing Strategy

### 5.1 Unit Tests
- Test each agent's decision logic
- Test credit scoring algorithm
- Test fraud detection rules
- Test NLP parsing accuracy

### 5.2 Integration Tests
- Test event flow end-to-end
- Test agent collaboration scenarios
- Test notification batching
- Test reorder approval workflow

### 5.3 Performance Tests
- Load test event processing (100+ events/sec)
- Test Redis pub/sub under load
- Test database query performance
- Test AI API response times

## 6. Deployment Strategy

### Phase 1: Foundation (Week 1-2)
- Deploy event-driven architecture
- Deploy Redis and configure pub/sub
- Add database triggers
- Test event flow

### Phase 2: Core Agents (Week 3-4)
- Deploy inventory orchestrator
- Deploy customer lifecycle manager
- Deploy credit system
- Test agent interactions

### Phase 3: Intelligence (Week 5-6)
- Deploy conversational AI
- Deploy BI system
- Deploy fraud detection
- Test end-to-end workflows

### Phase 4: Collaboration (Week 7-8)
- Deploy multi-agent system
- Deploy notification orchestrator
- Test collaboration scenarios
- Performance optimization

### Phase 5: Polish (Week 9-10)
- Monitoring and logging
- Documentation
- User training
- Production rollout

## 7. Monitoring & Observability

### Metrics to Track
- Event processing latency
- Agent decision accuracy
- API response times
- Fraud detection precision/recall
- Customer satisfaction scores
- Revenue impact

### Alerts
- Event processing failures
- Agent errors
- High fraud risk orders
- System performance degradation
- API rate limit approaching

## 8. Rollback Plan

Each feature has a feature flag that can be disabled:
- `ENABLE_EVENT_DRIVEN` - Fallback to polling
- `ENABLE_AUTO_REORDER` - Disable reorder suggestions
- `ENABLE_CONVERSATIONAL_AI` - Fallback to command-based
- `ENABLE_FRAUD_DETECTION` - Disable fraud checks
- `ENABLE_AGENT_COLLABORATION` - Agents work independently

## 9. Success Criteria

See requirements.md Section 5 for detailed success metrics.

---

**Document Version:** 1.0
**Last Updated:** 2026-02-15
**Status:** Ready for Implementation

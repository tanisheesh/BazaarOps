# Design Document: Telegram Kirana Store OS

## Overview

The Telegram Kirana Store OS is a multi-tenant system that enables Indian kirana shop owners to manage inventory and receive customer orders entirely through Telegram bots, powered by Claude AI for natural language understanding. The system consists of two Telegram bots (Owner Bot and Customer Bot), a FastAPI backend, and a PostgreSQL database.

### Key Design Principles

1. **Simplicity First**: Optimized for 7-hour hackathon build with 2 developers
2. **Telegram-Native**: No web interface, all interactions through Telegram
3. **AI-Powered NLU**: Claude handles natural language parsing, backend handles all logic
4. **Multi-Tenant**: Single deployment supports multiple independent stores
5. **Transaction Safety**: Inventory operations use database transactions to prevent race conditions
6. **Demo Stability**: Graceful error handling and fallback behaviors

## Architecture

### System Components

```
┌─────────────────┐         ┌─────────────────┐
│   Owner Bot     │         │  Customer Bot   │
│  (Telegram)     │         │   (Telegram)    │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │    Telegram Bot API       │
         │                           │
         └───────────┬───────────────┘
                     │
         ┌───────────▼────────────┐
         │   FastAPI Backend      │
         │  ┌──────────────────┐  │
         │  │ Bot Handlers     │  │
         │  ├──────────────────┤  │
         │  │ Claude Service   │  │
         │  ├──────────────────┤  │
         │  │ Business Logic   │  │
         │  ├──────────────────┤  │
         │  │ Database Layer   │  │
         │  └──────────────────┘  │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │   PostgreSQL Database  │
         │   (Supabase)           │
         └────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │   Claude API           │
         │   (Tool Use)           │
         └────────────────────────┘
```

### Request Flow Examples

**Owner Adding Stock:**
1. Owner sends "Add 50 packets of Maggi" to Owner Bot
2. Bot handler receives message, calls Claude Service
3. Claude Service sends to Claude API with tool definitions
4. Claude returns `add_stock(item_name="Maggi", quantity=50)`
5. Backend validates parameters
6. Backend updates inventory in database transaction
7. Backend sends confirmation to Owner Bot

**Customer Placing Order:**
1. Customer sends "I need 2 kg rice and 1 liter oil" to Customer Bot
2. Bot handler receives message, calls Claude Service
3. Claude returns `create_order(items=[{item_name="Rice", quantity=2}, {item_name="Oil", quantity=1}])`
4. Backend checks inventory availability
5. Backend sends confirmation message with inline keyboard
6. Customer clicks "Confirm"
7. Backend starts transaction, locks inventory rows, decrements stock, creates order
8. Backend notifies owner via Owner Bot
9. Backend confirms to customer

## Components and Interfaces

### 1. Telegram Bot Layer

**Owner Bot Handler**
- Handles `/start` command for onboarding
- Routes natural language messages to Claude Service
- Displays inline keyboards for order approval
- Manages conversation state per telegram_id

**Customer Bot Handler**
- Handles `/start` command with deep link parameter
- Extracts and validates store_id from deep link
- Routes natural language messages to Claude Service
- Displays order confirmation keyboards
- Manages conversation state per telegram_id

**Message Types:**
```python
# Incoming from Telegram
class TelegramMessage:
    telegram_id: int
    text: str
    chat_id: int
    message_id: int

# Outgoing to Telegram
class TelegramResponse:
    chat_id: int
    text: str
    reply_markup: Optional[InlineKeyboard]
    parse_mode: str = "Markdown"
```

### 2. Claude Service Layer

**Purpose:** Translate natural language to structured tool calls

**Tool Definitions:**

```python
tools = [
    {
        "name": "add_stock",
        "description": "Add or update inventory stock for an item",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item"},
                "quantity": {"type": "integer", "description": "Quantity to add"}
            },
            "required": ["item_name", "quantity"]
        }
    },
    {
        "name": "record_sale",
        "description": "Record a manual sale transaction",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item sold"},
                "quantity": {"type": "integer", "description": "Quantity sold"}
            },
            "required": ["item_name", "quantity"]
        }
    },
    {
        "name": "check_stock",
        "description": "Check availability and quantity of an item",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_name": {"type": "string", "description": "Name of the item to check"}
            },
            "required": ["item_name"]
        }
    },
    {
        "name": "create_order",
        "description": "Create a new customer order",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string"},
                            "quantity": {"type": "integer"}
                        },
                        "required": ["item_name", "quantity"]
                    }
                }
            },
            "required": ["items"]
        }
    }
]
```

**Claude Service Interface:**

```python
class ClaudeService:
    async def parse_message(
        self, 
        user_message: str, 
        context: str
    ) -> ToolCall | TextResponse:
        """
        Send message to Claude API with tool definitions.
        Returns either a tool call or a text response.
        """
        pass

class ToolCall:
    tool_name: str
    arguments: dict

class TextResponse:
    text: str
```

**Error Handling:**
- If Claude API fails: Return error, ask user to retry
- If response is malformed: Return error, ask user to rephrase
- No database mutations on Claude errors

### 3. Business Logic Layer

**Owner Service**

```python
class OwnerService:
    async def onboard_owner(
        self, 
        telegram_id: int, 
        store_name: str, 
        language: str
    ) -> OnboardingResult:
        """
        Create store and owner records.
        Generate customer bot deep link.
        """
        pass
    
    async def add_stock(
        self, 
        store_id: int, 
        item_name: str, 
        quantity: int
    ) -> StockUpdateResult:
        """
        Insert or update inventory record.
        Normalize item name for consistency.
        """
        pass
    
    async def record_sale(
        self, 
        store_id: int, 
        item_name: str, 
        quantity: int
    ) -> SaleResult:
        """
        Check stock availability.
        Decrement inventory in transaction.
        Create sales_log entry.
        """
        pass
    
    async def get_inventory(
        self, 
        store_id: int
    ) -> List[InventoryItem]:
        """
        Retrieve all inventory items for store.
        """
        pass
    
    async def get_low_stock_items(
        self, 
        store_id: int
    ) -> List[InventoryItem]:
        """
        Query items where current_stock < low_stock_threshold.
        """
        pass
    
    async def get_pending_orders(
        self, 
        store_id: int
    ) -> List[Order]:
        """
        Retrieve orders with status='pending'.
        """
        pass
    
    async def approve_order(
        self, 
        order_id: int
    ) -> ApprovalResult:
        """
        Update order status to 'accepted'.
        """
        pass
    
    async def reject_order(
        self, 
        order_id: int
    ) -> RejectionResult:
        """
        Update order status to 'rejected'.
        Restore inventory in transaction.
        """
        pass
```

**Customer Service**

```python
class CustomerService:
    async def register_customer(
        self, 
        telegram_id: int, 
        store_id: int, 
        customer_name: str
    ) -> RegistrationResult:
        """
        Create or update customer record.
        Map telegram_id to store_id.
        """
        pass
    
    async def check_stock(
        self, 
        store_id: int, 
        item_name: str
    ) -> StockCheckResult:
        """
        Query inventory for specific item.
        """
        pass
    
    async def get_catalog(
        self, 
        store_id: int
    ) -> List[InventoryItem]:
        """
        Retrieve all available items for store.
        """
        pass
    
    async def create_order(
        self, 
        customer_id: int, 
        store_id: int, 
        items: List[OrderItem]
    ) -> OrderCreationResult:
        """
        Start transaction with SELECT FOR UPDATE.
        Check all items availability.
        Decrement inventory atomically.
        Create order and order_items records.
        Commit transaction.
        """
        pass
```

### 4. Database Layer

**Schema Design:**

```sql
-- Stores table
CREATE TABLE stores (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    language_preference VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Owners table
CREATE TABLE owners (
    owner_id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory table
CREATE TABLE inventory (
    inventory_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, item_name)
);

-- Customers table
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    customer_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(telegram_id, store_id)
);

-- Orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id) ON DELETE CASCADE,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    total_items INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order items table
CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    price_snapshot DECIMAL(10, 2) DEFAULT 0
);

-- Sales logs table
CREATE TABLE sales_logs (
    sale_id SERIAL PRIMARY KEY,
    store_id INTEGER REFERENCES stores(store_id) ON DELETE CASCADE,
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL,
    sale_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_inventory_store_id ON inventory(store_id);
CREATE INDEX idx_customers_telegram_id ON customers(telegram_id);
CREATE INDEX idx_customers_store_id ON customers(store_id);
CREATE INDEX idx_orders_store_id ON orders(store_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_sales_logs_store_date ON sales_logs(store_id, sale_date);
```

**Transaction Pattern for Order Creation:**

```python
async def create_order_transaction(
    customer_id: int,
    store_id: int,
    items: List[OrderItem]
) -> OrderCreationResult:
    async with db.transaction():
        # Lock inventory rows for update
        for item in items:
            inventory = await db.fetch_one(
                """
                SELECT inventory_id, current_stock 
                FROM inventory 
                WHERE store_id = $1 AND item_name = $2
                FOR UPDATE
                """,
                store_id, item.item_name
            )
            
            if not inventory or inventory.current_stock < item.quantity:
                raise InsufficientStockError(item.item_name)
        
        # Decrement inventory
        for item in items:
            await db.execute(
                """
                UPDATE inventory 
                SET current_stock = current_stock - $1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE store_id = $2 AND item_name = $3
                """,
                item.quantity, store_id, item.item_name
            )
        
        # Create order
        order_id = await db.fetch_val(
            """
            INSERT INTO orders (customer_id, store_id, status, total_items)
            VALUES ($1, $2, 'pending', $3)
            RETURNING order_id
            """,
            customer_id, store_id, len(items)
        )
        
        # Create order items
        for item in items:
            await db.execute(
                """
                INSERT INTO order_items (order_id, item_name, quantity)
                VALUES ($1, $2, $3)
                """,
                order_id, item.item_name, item.quantity
            )
        
        return OrderCreationResult(order_id=order_id, success=True)
```

## Data Models

### Core Domain Models

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Store(BaseModel):
    store_id: int
    store_name: str
    language_preference: str
    created_at: datetime

class Owner(BaseModel):
    owner_id: int
    telegram_id: int
    store_id: int
    created_at: datetime

class InventoryItem(BaseModel):
    inventory_id: int
    store_id: int
    item_name: str
    current_stock: int
    low_stock_threshold: int
    created_at: datetime
    updated_at: datetime

class Customer(BaseModel):
    customer_id: int
    telegram_id: int
    store_id: int
    customer_name: Optional[str]
    created_at: datetime

class Order(BaseModel):
    order_id: int
    customer_id: int
    store_id: int
    status: str  # 'pending', 'accepted', 'rejected'
    total_items: int
    created_at: datetime
    updated_at: datetime
    items: List['OrderItem']

class OrderItem(BaseModel):
    order_item_id: Optional[int]
    order_id: Optional[int]
    item_name: str
    quantity: int
    price_snapshot: float = 0.0

class SaleLog(BaseModel):
    sale_id: int
    store_id: int
    item_name: str
    quantity: int
    sale_date: datetime
    created_at: datetime
```

### Item Name Normalization

To handle spelling variations and language differences:

```python
def normalize_item_name(raw_name: str) -> str:
    """
    Normalize item names for consistent matching.
    - Convert to lowercase
    - Remove extra whitespace
    - Trim leading/trailing spaces
    """
    return " ".join(raw_name.lower().strip().split())
```

## Correctness Properties


A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Multi-Tenant Data Isolation

*For any* two distinct stores A and B, querying inventory, customers, or orders for store A should never return records belonging to store B.

**Validates: Requirements 1.2, 1.3, 1.4**

### Property 2: Unique Store Identification

*For any* sequence of store registrations, each created store should receive a unique store_id that is never reused.

**Validates: Requirements 1.1**

### Property 3: Deep Link Store ID Extraction

*For any* valid deep link with format `t.me/CustomerBot?start=store_<N>`, the system should extract store_id N correctly, and for any malformed deep link, the system should reject it.

**Validates: Requirements 1.6**

### Property 4: Customer-Store Mapping Persistence

*For any* customer registration with telegram_id T and store_id S, subsequent lookups of telegram_id T should return store_id S.

**Validates: Requirements 1.7**

### Property 5: Idempotent Owner Registration

*For any* telegram_id, registering as an owner multiple times should create exactly one owner record and one store record.

**Validates: Requirements 2.8**

### Property 6: Tool Call Parameter Validation

*For any* tool call (add_stock, record_sale, check_stock, create_order), if parameters are invalid (negative quantities, empty item names, malformed structure), the system should reject the operation before any database mutation.

**Validates: Requirements 3.2**

### Property 7: Inventory Upsert Behavior

*For any* store and item name, calling add_stock should create a new inventory record if the item doesn't exist, or update the existing record's quantity if it does exist.

**Validates: Requirements 3.3**

### Property 8: Item Name Normalization

*For any* two item name strings that differ only in case, whitespace, or common spelling variations, the system should treat them as the same item in inventory operations.

**Validates: Requirements 3.7**

### Property 9: Sales Audit Trail

*For any* successful record_sale operation with item I and quantity Q, the system should create a sales_log entry with the same item name and quantity, and the inventory should be decremented by Q.

**Validates: Requirements 4.5, 4.6**

### Property 10: Low Stock Threshold Detection

*For any* inventory item, if current_stock < low_stock_threshold, the item should appear in the low stock list, and if current_stock >= low_stock_threshold, it should not appear.

**Validates: Requirements 5.2**

### Property 11: Order Acceptance State Transition

*For any* order with status 'pending', calling approve_order should change the status to 'accepted' and leave inventory unchanged.

**Validates: Requirements 6.4**

### Property 12: Order Rejection Inventory Restoration

*For any* order with status 'pending', calling reject_order should change the status to 'rejected' and restore the inventory quantities for all items in the order.

**Validates: Requirements 6.6**

### Property 13: Store Existence Validation

*For any* store_id S, if S does not exist in the stores table, customer registration with store_id S should be rejected.

**Validates: Requirements 7.2**

### Property 14: Customer Registration Upsert

*For any* telegram_id T and store_id S, calling register_customer should create a new customer record if (T, S) doesn't exist, or update the existing record if it does.

**Validates: Requirements 7.4**

### Property 15: Concurrent Inventory Safety

*For any* inventory item with current_stock N, if multiple concurrent operations (sales or orders) attempt to decrement stock, the final current_stock should never be negative, and the sum of all successful decrements should not exceed N.

**Validates: Requirements 11.11, 4.4, 8.4**

### Property 16: Order Creation Atomicity

*For any* order creation with items [I1, I2, ..., In] and quantities [Q1, Q2, ..., Qn], either all inventory items are decremented by their respective quantities and order records are created, or none of these changes occur (atomic transaction).

**Validates: Requirements 8.9**

### Property 17: Pending Order Deletion Prevention

*For any* inventory item that appears in at least one order with status 'pending', attempts to delete that inventory item should be rejected.

**Validates: Requirements 14.3**

## Error Handling

### Claude API Failures

**Strategy:** Fail gracefully without data corruption

- If Claude API is unreachable: Return error message, ask user to retry
- If Claude returns malformed JSON: Log error, ask user to rephrase
- If Claude returns unexpected tool name: Log error, ask user to rephrase
- Never perform database mutations when Claude response is invalid

**Implementation:**

```python
async def handle_claude_response(response: ClaudeResponse) -> Result:
    try:
        if response.stop_reason == "tool_use":
            tool_call = extract_tool_call(response)
            validate_tool_call(tool_call)  # Raises ValidationError if invalid
            return execute_tool(tool_call)
        else:
            return TextResult(response.content)
    except ClaudeAPIError:
        logger.error("Claude API unreachable", exc_info=True)
        return ErrorResult("Service temporarily unavailable. Please try again.")
    except ValidationError as e:
        logger.error(f"Invalid tool call: {e}", exc_info=True)
        return ErrorResult("I didn't understand that. Could you rephrase?")
```

### Database Errors

**Strategy:** Retry transient errors, fail fast on permanent errors

- Connection errors: Retry up to 3 times with exponential backoff
- Transaction conflicts: Rollback and notify user to retry
- Constraint violations: Return user-friendly error message
- Deadlocks: Should not occur with SELECT FOR UPDATE pattern

**Implementation:**

```python
@retry(max_attempts=3, backoff=exponential)
async def execute_with_retry(operation):
    try:
        return await operation()
    except asyncpg.PostgresConnectionError:
        logger.warning("Database connection error, retrying...")
        raise  # Trigger retry
    except asyncpg.UniqueViolationError as e:
        logger.info(f"Unique constraint violation: {e}")
        return ErrorResult("This record already exists.")
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        return ErrorResult("An error occurred. Please try again.")
```

### Telegram API Errors

**Strategy:** Queue and retry with rate limit handling

- Rate limit errors: Exponential backoff, queue messages
- Network errors: Retry up to 3 times
- Invalid chat_id: Log error, skip message
- Message too long: Truncate and add "..." indicator

**Implementation:**

```python
async def send_telegram_message(chat_id: int, text: str):
    try:
        await bot.send_message(chat_id, text)
    except TelegramRateLimitError as e:
        await asyncio.sleep(e.retry_after)
        await bot.send_message(chat_id, text)
    except TelegramNetworkError:
        await retry_with_backoff(lambda: bot.send_message(chat_id, text))
    except TelegramBadRequest as e:
        logger.error(f"Invalid Telegram request: {e}")
```

### Validation Errors

**Strategy:** Provide clear feedback to users

- Negative quantities: "Quantity must be positive"
- Empty item names: "Please provide an item name"
- Insufficient stock: "Only X units available"
- Invalid store_id: "Store not found"

### Edge Cases

**Empty Inventory:**
- Display: "No items in inventory yet. Add your first item!"
- Behavior: Allow adding first item normally

**Concurrent Order Conflicts:**
- Use SELECT FOR UPDATE to lock rows
- If stock becomes insufficient during transaction: Rollback, notify customer
- Message: "Sorry, this item just sold out. Please try a different quantity."

**Malformed Deep Links:**
- Invalid format: "Invalid store link. Please ask the store owner for a new link."
- Non-existent store_id: "This store is not available. Please contact the store owner."

**Item Name Variations:**
- Normalize before database operations
- "Maggi", "maggi", "MAGGI" → all map to "maggi"
- "Tata Salt", "tata  salt" → both map to "tata salt"

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests:** Verify specific examples, edge cases, and error conditions
- Specific example: Onboarding flow creates store and owner
- Edge case: Empty inventory displays correct message
- Error condition: Invalid store_id in deep link returns error
- Integration: Order notification reaches owner bot

**Property Tests:** Verify universal properties across all inputs
- Universal correctness: Concurrent orders never create negative inventory
- Comprehensive coverage: Item name normalization handles all case/whitespace variations
- Randomized inputs: Data isolation holds for any combination of stores and operations

### Property-Based Testing Configuration

**Library:** Use `hypothesis` for Python property-based testing

**Configuration:**
- Minimum 100 iterations per property test
- Each test references its design document property
- Tag format: `# Feature: telegram-kirana-store-os, Property N: [property text]`

**Example Property Test:**

```python
from hypothesis import given, strategies as st
import pytest

# Feature: telegram-kirana-store-os, Property 15: Concurrent Inventory Safety
@given(
    initial_stock=st.integers(min_value=10, max_value=100),
    order_quantities=st.lists(
        st.integers(min_value=1, max_value=20),
        min_size=2,
        max_size=5
    )
)
@pytest.mark.asyncio
async def test_concurrent_orders_never_negative_inventory(
    initial_stock: int,
    order_quantities: List[int]
):
    """
    Property: For any initial stock N and concurrent order quantities,
    final stock should never be negative.
    """
    # Setup: Create store and inventory item
    store_id = await create_test_store()
    item_name = "Test Item"
    await add_stock(store_id, item_name, initial_stock)
    
    # Execute: Simulate concurrent orders
    tasks = [
        create_order(store_id, [(item_name, qty)])
        for qty in order_quantities
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify: Final stock is never negative
    final_stock = await get_stock(store_id, item_name)
    assert final_stock >= 0
    
    # Verify: Sum of successful decrements <= initial stock
    successful_decrements = sum(
        qty for qty, result in zip(order_quantities, results)
        if not isinstance(result, Exception)
    )
    assert successful_decrements <= initial_stock
```

### Test Coverage Requirements

**Core Flows (Unit Tests):**
1. Owner onboarding creates store and generates deep link
2. Customer registration via deep link maps to correct store
3. Adding stock creates/updates inventory
4. Recording sale decrements inventory and creates log
5. Order creation decrements inventory atomically
6. Order acceptance changes status
7. Order rejection restores inventory
8. Low stock calculation flags items below threshold

**Correctness Properties (Property Tests):**
1. Multi-tenant data isolation (Property 1)
2. Concurrent inventory safety (Property 15)
3. Order creation atomicity (Property 16)
4. Item name normalization (Property 8)
5. Inventory upsert behavior (Property 7)
6. Customer upsert behavior (Property 14)
7. Sales audit trail (Property 9)
8. Order rejection restoration (Property 12)

**Edge Cases (Unit Tests):**
1. Empty inventory display
2. Unavailable item in order
3. Insufficient stock for sale
4. Malformed deep link
5. Non-existent store_id
6. Claude API failure
7. Database connection failure

**Integration Tests:**
1. End-to-end owner flow: onboard → add stock → receive order → approve
2. End-to-end customer flow: register → browse → place order → receive confirmation
3. Concurrent customers ordering same item
4. Owner and customer operations on same store simultaneously

### Demo Scenario Test

Create a comprehensive test that simulates the hackathon demo:

```python
async def test_demo_scenario():
    """
    Simulates complete demo flow:
    1. Owner onboards and adds inventory
    2. Customer registers via deep link
    3. Customer places order
    4. Owner receives and approves order
    5. Inventory is correctly updated
    """
    # Owner onboards
    owner_telegram_id = 123456
    store = await onboard_owner(
        owner_telegram_id,
        "Sharma Kirana Store",
        "en"
    )
    deep_link = store.customer_bot_link
    
    # Owner adds inventory
    await add_stock(store.store_id, "Rice", 50)
    await add_stock(store.store_id, "Oil", 20)
    await add_stock(store.store_id, "Sugar", 30)
    
    # Customer registers
    customer_telegram_id = 789012
    store_id = extract_store_id_from_link(deep_link)
    customer = await register_customer(
        customer_telegram_id,
        store_id,
        "Rajesh Kumar"
    )
    
    # Customer places order
    order = await create_order(
        customer.customer_id,
        store_id,
        [
            OrderItem(item_name="Rice", quantity=5),
            OrderItem(item_name="Oil", quantity=2)
        ]
    )
    
    # Verify inventory decremented
    rice_stock = await get_stock(store_id, "Rice")
    oil_stock = await get_stock(store_id, "Oil")
    assert rice_stock == 45
    assert oil_stock == 18
    
    # Owner approves order
    await approve_order(order.order_id)
    
    # Verify order status
    updated_order = await get_order(order.order_id)
    assert updated_order.status == "accepted"
```

This testing strategy ensures the system is stable for the hackathon demo while providing confidence in core correctness properties.

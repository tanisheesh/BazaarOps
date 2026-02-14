# Requirements Document

## Introduction

This document specifies requirements for a Telegram-based Store Operating System designed for Indian Kirana (small retail) shops. The system enables store owners to manage inventory and receive customer orders through natural language interactions powered by Claude AI, operating entirely within Telegram without any web interface.

## Glossary

- **System**: The Telegram Kirana Store OS
- **Owner_Bot**: Telegram bot interface for store owners
- **Customer_Bot**: Telegram bot interface for customers
- **Store**: A single retail shop entity with unique store_id
- **Owner**: A store owner who manages inventory and orders
- **Customer**: An end user who places orders through Customer_Bot
- **Claude_Service**: Claude AI API with Tool Use for natural language parsing
- **Backend**: FastAPI Python server handling business logic and database operations
- **Deep_Link**: Telegram URL format t.me/CustomerBot?start=store_<store_id>
- **Tool_Function**: Structured function definition for Claude Tool Use API
- **Low_Stock_Threshold**: Configurable minimum quantity triggering reorder alerts
- **Order**: Customer purchase request requiring owner approval
- **Sale**: Completed transaction reducing inventory
- **Multi_Tenant**: Architecture supporting multiple independent stores in single system

## Hackathon Scope Constraints

This system is designed for a 7-hour hackathon build with 2 developers. The following constraints apply:

- **No payments integration**: Orders are tracked but not paid through the system
- **No GST billing**: No tax calculations or invoice generation
- **No analytics dashboard**: No web-based reporting or visualization
- **No web frontend**: Telegram bots are the only user interface
- **Single FastAPI deployment**: One monolithic backend service
- **Stability prioritized over feature depth**: Core flows must work reliably for demo

## Requirements

### Requirement 1: Multi-Tenant Store Management

**User Story:** As a system architect, I want to support multiple independent stores in a single deployment, so that the system can scale to serve many kirana shops without separate infrastructure.

#### Acceptance Criteria

1. THE System SHALL assign a unique store_id to each registered store
2. THE System SHALL scope all inventory records to their parent store_id
3. THE System SHALL scope all customer records to their parent store_id
4. THE System SHALL scope all order records to their parent store_id
5. THE System SHALL prevent data leakage between different stores through database constraints
6. WHEN a customer accesses Customer_Bot via deep link, THE System SHALL extract and validate the store_id from the link parameter
7. THE System SHALL maintain a mapping between telegram_id and store_id for each customer

### Requirement 2: Owner Onboarding and Registration

**User Story:** As a store owner, I want to register my store through Owner_Bot, so that I can start managing my inventory via Telegram.

#### Acceptance Criteria

1. WHEN an unregistered telegram_id starts Owner_Bot, THE System SHALL initiate the onboarding flow
2. WHEN onboarding starts, THE System SHALL prompt for store name input
3. WHEN onboarding starts, THE System SHALL prompt for language preference selection between Hindi and English
4. WHEN onboarding completes, THE System SHALL create a store record with unique store_id
5. WHEN onboarding completes, THE System SHALL create an owner record linking telegram_id to store_id
6. WHEN onboarding completes, THE System SHALL generate a Customer_Bot deep link containing the store_id
7. WHEN onboarding completes, THE System SHALL display the shareable deep link to the owner
8. WHEN a registered telegram_id starts Owner_Bot, THE System SHALL skip onboarding and show the main menu

### Requirement 3: Owner Inventory Management

**User Story:** As a store owner, I want to add and update inventory using natural language, so that I can manage stock without learning complex commands.

#### Acceptance Criteria

1. WHEN an owner sends a natural language message about adding stock, THE System SHALL parse it using Claude_Service
2. WHEN Claude_Service returns add_stock tool call, THE Backend SHALL validate item_name and quantity parameters
3. WHEN add_stock is validated, THE Backend SHALL insert or update inventory record for the store_id
4. WHEN inventory is updated, THE System SHALL confirm the action to the owner in their preferred language
5. WHEN an owner requests to view inventory, THE System SHALL retrieve all items for their store_id and display them
6. WHEN inventory is empty, THE System SHALL display an appropriate empty state message
7. THE System SHALL handle spelling variations and mixed language input in item names

### Requirement 4: Owner Manual Sale Recording

**User Story:** As a store owner, I want to record manual sales through natural language, so that I can track inventory for in-person transactions.

#### Acceptance Criteria

1. WHEN an owner sends a natural language message about recording a sale, THE System SHALL parse it using Claude_Service
2. WHEN Claude_Service returns record_sale tool call, THE Backend SHALL validate item_name and quantity parameters
3. WHEN record_sale is validated, THE Backend SHALL check if sufficient stock exists
4. IF insufficient stock exists, THEN THE System SHALL reject the sale and notify the owner
5. WHEN sufficient stock exists, THE Backend SHALL decrement inventory within a database transaction
6. WHEN sale is recorded, THE Backend SHALL create a sales_log entry with timestamp and quantity
7. WHEN sale completes, THE System SHALL confirm the action and show updated stock level

### Requirement 5: Owner Low Stock Monitoring

**User Story:** As a store owner, I want to see which items are running low, so that I can reorder supplies before running out.

#### Acceptance Criteria

1. WHEN an owner requests low stock items, THE System SHALL calculate low stock status for all inventory items
2. THE System SHALL flag an item as low stock if current_stock is less than low_stock_threshold
3. WHEN low stock items are identified, THE System SHALL display them with current quantity
4. WHEN no items are low stock, THE System SHALL display an appropriate message

### Requirement 6: Owner Order Management

**User Story:** As a store owner, I want to review and approve customer orders, so that I can control what gets fulfilled from my inventory.

#### Acceptance Criteria

1. WHEN a customer submits an order, THE System SHALL notify the owner immediately via Owner_Bot
2. WHEN displaying an order notification, THE System SHALL show customer name, items, quantities, and total
3. WHEN displaying an order notification, THE System SHALL provide Accept and Reject inline keyboard buttons
4. WHEN an owner clicks Accept, THE Backend SHALL mark the order as accepted within a database transaction
5. WHEN an owner clicks Accept, THE System SHALL notify the customer via Customer_Bot
6. WHEN an owner clicks Reject, THE Backend SHALL mark the order as rejected and restore inventory
7. WHEN an owner clicks Reject, THE System SHALL notify the customer with rejection message
8. WHEN an owner requests pending orders, THE System SHALL display all orders with status pending for their store_id

### Requirement 7: Customer Registration via Deep Link

**User Story:** As a customer, I want to access a specific store's bot through a shared link, so that I can place orders at my local kirana shop.

#### Acceptance Criteria

1. WHEN a customer clicks a deep link with format t.me/CustomerBot?start=store_<store_id>, THE System SHALL extract the store_id parameter
2. WHEN store_id is extracted, THE System SHALL validate that the store exists in the database
3. IF store does not exist, THEN THE System SHALL display an error message and halt
4. WHEN store is validated, THE System SHALL create or update a customer record mapping telegram_id to store_id
5. WHEN customer registration completes, THE System SHALL display a welcome message with store name
6. WHEN a registered customer starts Customer_Bot without parameters, THE System SHALL use their existing store_id mapping

### Requirement 8: Customer Order Placement

**User Story:** As a customer, I want to place orders using natural language, so that I can shop conveniently without navigating complex menus.

#### Acceptance Criteria

1. WHEN a customer sends a natural language order message, THE System SHALL parse it using Claude_Service
2. WHEN Claude_Service returns create_order tool call, THE Backend SHALL validate the items list structure
3. WHEN items are validated, THE Backend SHALL check availability for each item in the customer's store inventory
4. IF any item is unavailable or has insufficient stock, THEN THE System SHALL notify the customer and halt order creation
5. WHEN all items are available, THE System SHALL display an order confirmation with items, quantities, and total
6. WHEN displaying confirmation, THE System SHALL provide Confirm and Cancel inline keyboard buttons
7. WHEN customer clicks Cancel, THE System SHALL discard the order and return to main menu
8. WHEN customer clicks Confirm, THE Backend SHALL execute order creation within a database transaction
9. WHEN order is confirmed, THE Backend SHALL decrement inventory for all items atomically
10. WHEN order is confirmed, THE Backend SHALL create order and order_items records with status pending
11. WHEN order is confirmed, THE System SHALL notify the owner via Owner_Bot
12. WHEN order is confirmed, THE System SHALL display a success message to the customer

### Requirement 9: Customer Catalog Browsing

**User Story:** As a customer, I want to view available items and check stock, so that I know what I can order.

#### Acceptance Criteria

1. WHEN a customer requests the catalog, THE System SHALL retrieve all inventory items for their mapped store_id
2. WHEN displaying catalog, THE System SHALL show item names and availability status
3. WHEN catalog is empty, THE System SHALL display an appropriate message
4. WHEN a customer asks about a specific item, THE System SHALL parse the query using Claude_Service
5. WHEN Claude_Service returns check_stock tool call, THE Backend SHALL query inventory for the item
6. WHEN item exists, THE System SHALL display availability and quantity
7. WHEN item does not exist, THE System SHALL inform the customer it is unavailable

### Requirement 10: Claude Tool Use Integration

**User Story:** As a system architect, I want Claude to only parse natural language and return structured tool calls, so that all business logic and calculations remain in the backend.

#### Acceptance Criteria

1. THE System SHALL define tool functions: add_stock, record_sale, check_stock, create_order
2. WHEN calling Claude API, THE System SHALL provide tool definitions with parameter schemas
3. WHEN Claude returns a tool call, THE Backend SHALL extract the function name and arguments
4. THE Backend SHALL perform all stock calculations, not Claude_Service
5. THE Backend SHALL perform all database writes, not Claude_Service
6. THE Backend SHALL perform all validation logic, not Claude_Service
7. IF Claude returns malformed tool response, THEN THE System SHALL handle the error gracefully and prompt user to rephrase
8. THE System SHALL not expose database schema or business logic to Claude prompts

### Requirement 11: Database Schema and Integrity

**User Story:** As a system architect, I want a properly normalized database schema with constraints, so that data integrity is maintained under concurrent access.

#### Acceptance Criteria

1. THE System SHALL implement a stores table with columns: store_id (PK), store_name, language_preference, created_at
2. THE System SHALL implement an owners table with columns: owner_id (PK), telegram_id (unique), store_id (FK), created_at
3. THE System SHALL implement an inventory table with columns: inventory_id (PK), store_id (FK), item_name, current_stock, low_stock_threshold, created_at, updated_at
4. THE System SHALL implement a customers table with columns: customer_id (PK), telegram_id, store_id (FK), customer_name, created_at
5. THE System SHALL implement an orders table with columns: order_id (PK), customer_id (FK), store_id (FK), status, total_items, created_at, updated_at
6. THE System SHALL implement an order_items table with columns: order_item_id (PK), order_id (FK), item_name, quantity, price_snapshot
7. THE System SHALL implement a sales_logs table with columns: sale_id (PK), store_id (FK), item_name, quantity, sale_date, created_at
8. THE System SHALL create indexes on: store_id columns, telegram_id columns, order status, sale_date
9. THE System SHALL enforce foreign key constraints with appropriate cascade rules
10. WHEN decrementing inventory for orders, THE Backend SHALL use database transactions with row-level locking
11. WHEN two customers order the same item simultaneously, THE System SHALL prevent negative inventory through transaction isolation

### Requirement 12: Concurrent Order Handling

**User Story:** As a system architect, I want to prevent race conditions when multiple customers order the same item, so that inventory never goes negative.

#### Acceptance Criteria

1. WHEN processing an order confirmation, THE Backend SHALL begin a database transaction
2. WHEN checking item availability, THE Backend SHALL use SELECT FOR UPDATE to lock inventory rows
3. WHEN all items are available, THE Backend SHALL decrement inventory and create order records within the same transaction
4. IF any item becomes unavailable during the transaction, THEN THE Backend SHALL rollback and notify the customer
5. WHEN transaction commits successfully, THE System SHALL proceed with owner notification

### Requirement 13: Language Detection and Response

**User Story:** As a user, I want the system to understand and respond in my preferred language, so that I can interact naturally in Hindi or English.

#### Acceptance Criteria

1. WHEN a user sends a message to Claude_Service, THE System SHALL include the message in the original language
2. WHEN Claude_Service generates a response, THE System SHALL return it in the same language as the user's input
3. THE System SHALL handle mixed language input by relying on Claude's language understanding
4. THE System SHALL tolerate common spelling variations in item names across languages
5. WHEN storing item names, THE System SHALL normalize them to a consistent format for matching

### Requirement 14: Error Handling and Edge Cases

**User Story:** As a system architect, I want comprehensive error handling for edge cases, so that the system remains stable during the hackathon demo.

#### Acceptance Criteria

1. WHEN a customer orders an unavailable item, THE System SHALL list which items are unavailable and halt order creation
2. WHEN inventory would go negative, THE System SHALL prevent the operation and display current stock
3. WHEN an owner tries to delete an item with pending orders, THE System SHALL prevent deletion and show pending order count
4. WHEN Claude returns a malformed response, THE System SHALL log the error and ask the user to rephrase
5. WHEN database connection fails, THE System SHALL retry up to 3 times before showing error message
6. WHEN Telegram API rate limit is hit, THE System SHALL queue messages and retry with exponential backoff
7. WHEN an invalid store_id is provided in deep link, THE System SHALL display a friendly error message
8. THE System SHALL log all errors with context for debugging without exposing internals to users

### Requirement 15: Telegram User Experience Design

**User Story:** As a user, I want clear, intuitive interactions with inline keyboards and confirmations, so that I can complete tasks efficiently.

#### Acceptance Criteria

1. WHEN displaying menus, THE System SHALL use inline keyboards with clear button labels
2. WHEN an action requires confirmation, THE System SHALL display a summary and Confirm/Cancel buttons
3. WHEN an action completes successfully, THE System SHALL display a success message with relevant details
4. WHEN an error occurs, THE System SHALL display a user-friendly error message without technical jargon
5. WHEN displaying lists, THE System SHALL format them clearly with emojis for visual scanning
6. WHEN an owner receives an order notification, THE System SHALL format it with customer details and Accept/Reject buttons
7. WHEN a customer receives order status updates, THE System SHALL include order summary and next steps
8. THE System SHALL provide a help command listing available actions in the user's language

### Requirement 16: Demo Stability and Deployment

**User Story:** As a developer, I want a single deployable backend with minimal dependencies, so that the demo runs reliably during the hackathon presentation.

#### Acceptance Criteria

1. THE System SHALL be deployable as a single FastAPI application
2. THE System SHALL use PostgreSQL as the only database dependency
3. THE System SHALL be compatible with Supabase PostgreSQL hosting
4. THE System SHALL include environment variable configuration for: Telegram bot tokens, Claude API key, database URL
5. THE System SHALL include a database migration script to initialize schema
6. THE System SHALL include a health check endpoint returning system status
7. THE System SHALL gracefully handle startup when database is not yet ready
8. THE System SHALL include logging configuration for debugging during demo
9. THE System SHALL not require any web frontend or dashboard
10. THE System SHALL not include payment processing or GST billing features

### Requirement 17: Fallback Behavior

**User Story:** As a system architect, I want safe fallback behavior when AI services fail, so that the system never corrupts data due to API errors.

#### Acceptance Criteria

1. IF Claude API fails to respond, THEN THE System SHALL display an error message asking the user to try again
2. IF Claude returns a malformed tool response, THEN THE System SHALL ask the user to rephrase their request
3. WHEN Claude API fails or returns malformed response, THE System SHALL NOT perform any database mutation
4. WHEN Claude API fails or returns malformed response, THE System SHALL log the error with full context for debugging
5. THE System SHALL validate all tool call parameters before executing any database operations
6. IF tool call parameters are invalid, THEN THE System SHALL reject the operation and explain what is needed


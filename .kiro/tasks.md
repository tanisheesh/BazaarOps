# Implementation Plan: Telegram Kirana Store OS

## Overview

This implementation plan breaks down the Telegram Kirana Store OS into discrete coding tasks optimized for a 7-hour hackathon build with 2 developers. Tasks are ordered to enable incremental progress with early validation of core functionality. The system uses Python with FastAPI, PostgreSQL, python-telegram-bot library, and Claude API.

## Tasks

- [ ] 1. Project setup and database schema
  - Create FastAPI project structure with main.py, requirements.txt
  - Define environment variables: TELEGRAM_OWNER_BOT_TOKEN, TELEGRAM_CUSTOMER_BOT_TOKEN, CLAUDE_API_KEY, DATABASE_URL
  - Create database migration script with all tables (stores, owners, inventory, customers, orders, order_items, sales_logs)
  - Add indexes for performance (store_id, telegram_id, order status)
  - Create health check endpoint GET /health
  - _Requirements: 11.1-11.9, 16.1-16.5_

- [ ] 2. Database layer and core models
  - [ ] 2.1 Implement Pydantic models for all domain entities
    - Create models: Store, Owner, InventoryItem, Customer, Order, OrderItem, SaleLog
    - Add validation rules for quantities (positive integers), item names (non-empty)
    - _Requirements: 11.1-11.9_
  
  - [ ] 2.2 Implement database connection and transaction utilities
    - Create async database connection pool using asyncpg
    - Implement transaction context manager for atomic operations
    - Add retry logic for connection errors (3 attempts, exponential backoff)
    - _Requirements: 12.1-12.5, 14.5_
  
  - [ ]* 2.3 Write property test for database transaction isolation
    - **Property 15: Concurrent Inventory Safety**
    - **Validates: Requirements 11.11**

- [ ] 3. Item name normalization utility
  - [ ] 3.1 Implement normalize_item_name function
    - Convert to lowercase, remove extra whitespace, trim
    - Handle common spelling variations
    - _Requirements: 3.7, 13.4_
  
  - [ ]* 3.2 Write property test for name normalization
    - **Property 8: Item Name Normalization**
    - **Validates: Requirements 3.7**

- [ ] 4. Owner service implementation
  - [ ] 4.1 Implement onboard_owner function
    - Create store record with unique store_id
    - Create owner record linking telegram_id to store_id
    - Generate Customer Bot deep link: f"t.me/CustomerBot?start=store_{store_id}"
    - Return OnboardingResult with store details and deep link
    - _Requirements: 2.1-2.7_
  
  - [ ]* 4.2 Write property test for idempotent owner registration
    - **Property 5: Idempotent Owner Registration**
    - **Validates: Requirements 2.8**
  
  - [ ] 4.3 Implement add_stock function
    - Normalize item name
    - Use INSERT ... ON CONFLICT to upsert inventory
    - Return updated stock level
    - _Requirements: 3.2-3.3_
  
  - [ ]* 4.4 Write property test for inventory upsert
    - **Property 7: Inventory Upsert Behavior**
    - **Validates: Requirements 3.3**
  
  - [ ] 4.5 Implement record_sale function
    - Check if sufficient stock exists
    - Start transaction with SELECT FOR UPDATE on inventory
    - Decrement inventory and create sales_log entry
    - Commit transaction
    - Return SaleResult with updated stock
    - _Requirements: 4.3-4.6_
  
  - [ ]* 4.6 Write property test for sales audit trail
    - **Property 9: Sales Audit Trail**
    - **Validates: Requirements 4.5, 4.6**
  
  - [ ] 4.7 Implement get_inventory and get_low_stock_items functions
    - Query all inventory for store_id
    - Filter items where current_stock < low_stock_threshold
    - _Requirements: 3.5, 5.1-5.2_
  
  - [ ]* 4.8 Write property test for low stock detection
    - **Property 10: Low Stock Threshold Detection**
    - **Validates: Requirements 5.2**
  
  - [ ] 4.9 Implement get_pending_orders, approve_order, reject_order functions
    - Query orders with status='pending' for store_id
    - Update order status to 'accepted' or 'rejected'
    - For rejection: restore inventory in transaction
    - _Requirements: 6.4-6.7_
  
  - [ ]* 4.10 Write property test for order rejection restoration
    - **Property 12: Order Rejection Inventory Restoration**
    - **Validates: Requirements 6.6**

- [ ] 5. Checkpoint - Core owner service complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Customer service implementation
  - [ ] 6.1 Implement register_customer function
    - Validate store_id exists in stores table
    - Use INSERT ... ON CONFLICT to upsert customer record
    - Map telegram_id to store_id
    - _Requirements: 7.2-7.4_
  
  - [ ]* 6.2 Write property test for store existence validation
    - **Property 13: Store Existence Validation**
    - **Validates: Requirements 7.2**
  
  - [ ] 6.3 Implement check_stock and get_catalog functions
    - Query inventory for specific item or all items
    - Return availability status
    - _Requirements: 9.4-9.7_
  
  - [ ] 6.4 Implement create_order function with transaction safety
    - Start transaction
    - Use SELECT FOR UPDATE to lock inventory rows
    - Check all items have sufficient stock
    - Decrement inventory for all items
    - Create order record with status='pending'
    - Create order_items records
    - Commit transaction
    - If any item insufficient: rollback and return error
    - _Requirements: 8.8-8.10, 12.1-12.5_
  
  - [ ]* 6.5 Write property test for order creation atomicity
    - **Property 16: Order Creation Atomicity**
    - **Validates: Requirements 8.9**
  
  - [ ]* 6.6 Write property test for concurrent order safety
    - **Property 15: Concurrent Inventory Safety**
    - **Validates: Requirements 11.11**

- [ ] 7. Claude service integration
  - [ ] 7.1 Implement Claude API client with tool definitions
    - Define tools: add_stock, record_sale, check_stock, create_order
    - Create tool schemas with parameter validation
    - Implement parse_message function that calls Claude API
    - Extract tool_use from response
    - Handle errors: API failures, malformed responses
    - _Requirements: 10.1-10.8_
  
  - [ ] 7.2 Implement tool call validation
    - Validate tool_name is one of defined tools
    - Validate arguments match schema (positive quantities, non-empty names)
    - Return ValidationError for invalid calls
    - _Requirements: 3.2, 17.5_
  
  - [ ]* 7.3 Write unit tests for Claude error handling
    - Test API failure returns error message
    - Test malformed response asks user to rephrase
    - Test no database mutation on errors
    - _Requirements: 17.1-17.4_

- [ ] 8. Owner Bot Telegram handler
  - [ ] 8.1 Implement /start command handler for onboarding
    - Check if telegram_id exists in owners table
    - If not: start onboarding flow (ask store name, language)
    - If yes: show main menu
    - _Requirements: 2.1-2.8_
  
  - [ ] 8.2 Implement natural language message handler
    - Send message to Claude service
    - Route tool calls to appropriate owner service functions
    - Handle text responses from Claude
    - Display results with inline keyboards where appropriate
    - _Requirements: 3.1-3.4_
  
  - [ ] 8.3 Implement inline keyboard handlers for order approval
    - Handle "Accept" button: call approve_order, notify customer
    - Handle "Reject" button: call reject_order, notify customer
    - _Requirements: 6.4-6.7_
  
  - [ ]* 8.4 Write integration test for owner onboarding flow
    - Test complete flow from /start to deep link generation
    - _Requirements: 2.1-2.7_

- [ ] 9. Customer Bot Telegram handler
  - [ ] 9.1 Implement /start command handler with deep link parsing
    - Extract store_id from start parameter: /start store_<store_id>
    - Validate store exists
    - Register customer with store_id
    - Display welcome message with store name
    - _Requirements: 7.1-7.6_
  
  - [ ]* 9.2 Write property test for deep link parsing
    - **Property 3: Deep Link Store ID Extraction**
    - **Validates: Requirements 1.6**
  
  - [ ] 9.3 Implement natural language message handler
    - Send message to Claude service
    - Route tool calls to appropriate customer service functions
    - For create_order: display confirmation with inline keyboard
    - Handle text responses from Claude
    - _Requirements: 8.1-8.4_
  
  - [ ] 9.4 Implement order confirmation keyboard handler
    - Handle "Confirm" button: call create_order, notify owner
    - Handle "Cancel" button: discard order, return to menu
    - Display success or error messages
    - _Requirements: 8.5-8.12_
  
  - [ ]* 9.5 Write integration test for customer order flow
    - Test complete flow from deep link to order confirmation
    - _Requirements: 8.1-8.12_

- [ ] 10. Checkpoint - Bot handlers complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Multi-tenant data isolation
  - [ ]* 11.1 Write property test for data isolation
    - **Property 1: Multi-Tenant Data Isolation**
    - **Validates: Requirements 1.2, 1.3, 1.4**
  
  - [ ]* 11.2 Write property test for customer-store mapping
    - **Property 4: Customer-Store Mapping Persistence**
    - **Validates: Requirements 1.7**

- [ ] 12. Error handling and edge cases
  - [ ] 12.1 Implement error handlers for all services
    - Wrap database operations with try-except for connection errors
    - Wrap Claude API calls with try-except for API errors
    - Return user-friendly error messages
    - Log all errors with context
    - _Requirements: 14.4-14.8, 17.1-17.6_
  
  - [ ] 12.2 Implement edge case handlers
    - Empty inventory: display appropriate message
    - Unavailable items in order: list unavailable items
    - Insufficient stock: display current stock level
    - Malformed deep link: display error message
    - _Requirements: 3.6, 8.4, 14.1-14.2_
  
  - [ ]* 12.3 Write unit tests for edge cases
    - Test empty inventory display
    - Test unavailable item error
    - Test insufficient stock error
    - Test malformed deep link error
    - _Requirements: 3.6, 8.4, 9.7, 14.1-14.2_

- [ ] 13. Message formatting and UI
  - [ ] 13.1 Create message templates for all bot responses
    - Onboarding messages (store created, deep link display)
    - Confirmation messages (stock added, sale recorded)
    - Order notifications (owner receives order, customer receives status)
    - Error messages (unavailable items, insufficient stock)
    - Use emojis for visual clarity
    - _Requirements: 15.1-15.8_
  
  - [ ] 13.2 Implement inline keyboard builders
    - Order approval keyboard (Accept/Reject buttons)
    - Order confirmation keyboard (Confirm/Cancel buttons)
    - Main menu keyboards for both bots
    - _Requirements: 15.1-15.2_

- [ ] 14. Deployment preparation
  - [ ] 14.1 Create requirements.txt with all dependencies
    - fastapi, uvicorn, asyncpg, python-telegram-bot, anthropic, pydantic
    - _Requirements: 16.1-16.2_
  
  - [ ] 14.2 Create .env.example file with all required environment variables
    - Document each variable's purpose
    - _Requirements: 16.4_
  
  - [ ] 14.3 Create README.md with setup instructions
    - Database setup steps
    - Environment variable configuration
    - Running the application
    - Testing the demo scenario
    - _Requirements: 16.1-16.10_
  
  - [ ] 14.4 Add logging configuration
    - Configure structured logging for debugging
    - Log all Claude API calls and responses
    - Log all database transactions
    - _Requirements: 16.8_

- [ ] 15. Demo scenario validation
  - [ ]* 15.1 Write end-to-end demo test
    - Test complete demo flow: owner onboards → adds stock → customer registers → places order → owner approves
    - Verify all state changes and notifications
    - _Requirements: All requirements_
  
  - [ ] 15.2 Manual demo walkthrough
    - Test both bots in Telegram
    - Verify natural language understanding
    - Verify concurrent order handling
    - Verify error messages are user-friendly

- [ ] 16. Final checkpoint - System complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and integration tests
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties using hypothesis library
- Unit tests validate specific examples and edge cases
- Focus on demo stability: graceful error handling, clear user feedback
- Two developers can work in parallel: one on Owner Bot + services, one on Customer Bot + Claude integration

# Advanced Agentic Features - Requirements

## 1. Overview
Transform BazaarOps into a fully autonomous, AI-powered store management system with advanced agentic capabilities where AI agents collaborate, learn, and make intelligent decisions.

## 2. User Stories

### 2.1 As a Store Owner
- I want the system to automatically detect low stock and suggest reorders so I don't run out of products
- I want to approve/reject AI reorder suggestions before they're sent to suppliers
- I want AI to predict which customers might stop ordering so I can re-engage them
- I want automatic birthday wishes sent to VIP customers to improve loyalty
- I want smart payment reminders sent at the right time to improve collections
- I want credit scores calculated automatically to manage risk
- I want AI to analyze my business and provide actionable insights
- I want to see trends, anomalies, and predictions in my dashboard
- I want agents to work together intelligently to solve problems
- I want fraud detection to protect my business from bad actors

### 2.2 As a Customer
- I want to order products using natural language (not rigid commands)
- I want the bot to understand "I need 2kg rice and 1kg sugar"
- I want personalized recommendations based on my purchase history
- I want to know my available credit limit before ordering
- I want notifications sent at convenient times (not late night)
- I want the bot to remember my preferences and usual orders

### 2.3 As the System
- I want to process events in real-time (not polling)
- I want agents to communicate and collaborate on decisions
- I want to learn from outcomes and improve over time
- I want to prevent fraud automatically while minimizing false positives
- I want to optimize notification timing based on customer behavior

## 3. Acceptance Criteria

### 3.1 Real-Time Event-Driven Architecture
- [ ] Order placement reduces inventory within 2 seconds
- [ ] Low stock triggers reorder agent within 5 seconds
- [ ] Payment updates trigger credit score recalculation immediately
- [ ] All events are logged and traceable
- [ ] Zero polling, 100% event-driven system
- [ ] Event processing handles 100+ events per second

### 3.2 Autonomous Inventory Orchestrator
- [ ] System detects low stock automatically
- [ ] Demand forecasting predicts next 7-14 days with >70% accuracy
- [ ] Owner receives reorder approval request with all details (product, stock, forecast, cost)
- [ ] Approval request has inline buttons: Approve, Edit Quantity, Reject
- [ ] On approval, WhatsApp message sent to supplier automatically
- [ ] System learns from owner's edits and adjusts future suggestions
- [ ] Reorder history tracked in database

### 3.3 Intelligent Customer Lifecycle Manager
- [ ] VIP customers identified automatically (top 20% by revenue)
- [ ] Birthday field collected during onboarding (optional)
- [ ] Birthday wishes sent at 9 AM with personalized message
- [ ] Churn risk detected when customer inactive >15 days
- [ ] Re-engagement messages sent automatically (no discounts)
- [ ] Second message sent if no response in 7 days
- [ ] Track: Birthday redemption rate, churn prevention success rate

### 3.4 Predictive Credit & Collection System
- [ ] Credit score calculated automatically (0-100 scale)
- [ ] Credit limits enforced in customer bot
- [ ] Score >70: Auto-approve up to ₹5000
- [ ] Score 50-70: Auto-approve up to ₹2000
- [ ] Score <50: Cash only
- [ ] Payment reminders sent at optimal times (learned per customer)
- [ ] Escalation strategy: Day 3 (friendly), Day 7 (firm), Day 15 (urgent), Day 30 (suspend)
- [ ] Auto-suspend credit if 30+ days overdue
- [ ] Auto-restore credit after payment
- [ ] Default prediction with >60% accuracy

### 3.5 Conversational AI Shopping Assistant
- [ ] Understands natural language orders: "I need 2kg rice and 1kg sugar"
- [ ] Handles Hindi/English mix: "2 kilo chawal"
- [ ] Fuzzy matching for typos: "rce" → "rice"
- [ ] Asks clarifying questions when ambiguous
- [ ] Maintains conversation context (last 5 messages)
- [ ] Offers "Same as last time?" for repeat customers
- [ ] Confirms order before placing
- [ ] >90% order understanding accuracy

### 3.6 Autonomous Business Intelligence System
- [ ] Trend detection: Week-over-week sales comparison
- [ ] Identifies top/bottom performing products
- [ ] Anomaly detection: Alerts on unusual patterns
- [ ] Profitability analysis per product and customer
- [ ] Revenue forecasting with 20% accuracy
- [ ] Stockout predictions with 80% accuracy
- [ ] Comprehensive daily BI report sent to owner
- [ ] Analytics dashboard with charts and insights

### 3.7 Multi-Agent Collaboration System
- [ ] Agents communicate via message bus
- [ ] Coordination working for low stock scenario
- [ ] Coordination working for customer churn scenario
- [ ] Coordination working for credit risk scenario
- [ ] Conflict resolution when agents disagree
- [ ] Goal-oriented behavior (owner sets goals, agents align)
- [ ] All decisions logged and traceable
- [ ] Measurable improvement in outcomes

### 3.8 Smart Notification Orchestrator
- [ ] Learns optimal notification time per customer
- [ ] Enforces max 3 messages per customer per day
- [ ] Batches multiple events into one message
- [ ] Personalizes tone, emojis, language per customer
- [ ] Only sends between 9 AM - 9 PM
- [ ] Response rate improved by 20%+
- [ ] Zero spam complaints

### 3.9 Autonomous Fraud Detection & Prevention
- [ ] Risk scoring for all orders (0-100 scale)
- [ ] High risk (>80): Block credit, require verification
- [ ] Medium risk (50-80): Ask for confirmation
- [ ] Low risk (<50): Auto-approve
- [ ] Detects: New customer large orders, multiple orders, unusual patterns
- [ ] Auto-blocks repeat offenders
- [ ] Owner notified of suspicious activity
- [ ] False positive rate <10%
- [ ] Fraud detection precision >80%

## 4. Technical Requirements

### 4.1 Infrastructure
- Redis for pub/sub messaging and caching
- PostgreSQL triggers for event generation
- Celery for background job processing
- Supabase real-time subscriptions

### 4.2 AI/ML
- Claude API for natural language processing
- Demand forecasting using historical data
- Credit scoring algorithm
- Fraud detection risk scoring
- Sentiment analysis for customer messages

### 4.3 Performance
- API response time <200ms (p95)
- Event processing time <5 seconds
- System uptime 99.5%+
- Handle 100+ concurrent users
- Database queries optimized with indexes

### 4.4 Security
- Input validation on all endpoints
- Rate limiting to prevent abuse
- Fraud detection in real-time
- Data encryption at rest and in transit
- Audit logs for all agent decisions

## 5. Success Metrics

### 5.1 Business Metrics
- Revenue increase: 30%+
- Customer retention: 80%+
- Average order value: 20% increase
- Credit collection rate: 90%+
- Stockout incidents: 50% reduction

### 5.2 Technical Metrics
- Reorder forecast accuracy: >70%
- Churn prediction accuracy: >60%
- Credit default prediction: >60%
- Fraud detection precision: >80%
- NLP order understanding: >90%
- Revenue forecast accuracy: Within 20%

## 6. Out of Scope
- Dynamic pricing optimization (removed per user request)
- Supplier-side portal (future phase)
- Stock balancing across multiple stores (future phase)
- Voice ordering (future phase)
- WhatsApp Business API integration (future phase)
- Payment gateway integration (future phase)

## 7. Dependencies
- Existing BazaarOps system (owner service, customer service, agent service)
- Telegram bots (owner bot, customer bot)
- Supabase database
- Claude API access
- Redis server
- Celery workers

## 8. Risks & Mitigation

### 8.1 AI API Costs
**Risk:** High Claude API usage costs
**Mitigation:** Cache responses, batch requests, use cheaper models for simple tasks

### 8.2 False Fraud Positives
**Risk:** Blocking legitimate customers
**Mitigation:** Manual review queue, learning system, adjustable thresholds

### 8.3 Over-automation
**Risk:** System making wrong decisions without human oversight
**Mitigation:** Owner approval for critical actions, override mechanisms

### 8.4 Event System Failures
**Risk:** Events lost or delayed
**Mitigation:** Dead letter queues, retry mechanisms, fallback to polling

## 9. Assumptions
- Store owners have Telegram accounts
- Customers have Telegram accounts
- Internet connectivity available
- Anthropic API remains available and affordable
- Supabase service remains stable
- Historical data available for forecasting (at least 30 days)

## 10. Constraints
- Must work on existing infrastructure
- Must maintain backward compatibility
- Must not break existing features
- Must be deployable on Render free tier initially
- Must handle graceful degradation if AI APIs fail

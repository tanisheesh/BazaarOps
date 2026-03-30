-- Migration 009: Agent Collaboration Tables
-- Creates tables for inter-agent messaging and decision logging

CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,
    message_type VARCHAR(100) NOT NULL,
    data JSONB,
    priority INTEGER DEFAULT 5,
    correlation_id UUID,
    store_id UUID,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_agents JSONB,
    decision_type VARCHAR(100) NOT NULL,
    input_data JSONB,
    output_decision JSONB,
    goal_used VARCHAR(50),
    store_id UUID,
    outcome VARCHAR(50),
    outcome_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_type ON agent_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_agent_messages_store ON agent_messages(store_id);
CREATE INDEX IF NOT EXISTS idx_agent_decisions_store ON agent_decisions(store_id);
CREATE INDEX IF NOT EXISTS idx_agent_decisions_type ON agent_decisions(decision_type);

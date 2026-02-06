-- PostgreSQL + pgvector setup for semantic health analysis
-- Run this on your new PostgreSQL database

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Health events with semantic embeddings
CREATE TABLE health_events (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    event_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,  -- "took magnesium 400mg at 10pm, slept great"
    embedding vector(1536),     -- OpenAI text-embedding-ada-002 dimension
    structured_data JSONB,      -- Extracted: {supplement: "magnesium", dosage: "400mg", time: "22:00", effects: ["relaxed"]}
    tags TEXT[],               -- Auto-generated: ["supplement", "evening", "sleep_aid"]
    outcome_metrics JSONB,     -- Next-day metrics: {sleep_score: 85, hrv: 45, energy: 8}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semantic correlation insights
CREATE TABLE semantic_correlations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    correlation_name VARCHAR(200) NOT NULL,  -- "magnesium_sleep_quality"
    correlation_value DECIMAL(5,4),          -- 0.67
    description TEXT,                        -- "Magnesium supplementation correlates with improved sleep quality"
    embedding vector(1536),                  -- Semantic representation
    supporting_events INTEGER[],             -- IDs of health_events that support this correlation
    discovery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    strength VARCHAR(20) DEFAULT 'moderate', -- weak, moderate, strong
    significance BOOLEAN DEFAULT FALSE
);

-- Pattern insights for SMS context
CREATE TABLE pattern_insights (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    pattern_type VARCHAR(50),     -- "similar_period", "successful_intervention", "decline_recovery"
    pattern_description TEXT,     -- "Similar HRV and sleep patterns led to 15% energy boost"
    embedding vector(1536),       -- Semantic representation of the pattern
    reference_period_start DATE,  -- When this pattern occurred
    reference_period_end DATE,
    interventions JSONB,          -- What was done: [{"type": "supplement", "name": "magnesium", "timing": "evening"}]
    outcomes JSONB,               -- Results: {"sleep_improvement": 15, "energy_boost": 23}
    confidence_score DECIMAL(3,2), -- How confident we are in this pattern (0.0-1.0)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast similarity search
CREATE INDEX ON health_events USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON semantic_correlations USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON pattern_insights USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Regular indexes for filtering
CREATE INDEX idx_health_events_user_date ON health_events(user_id, event_date DESC);
CREATE INDEX idx_health_events_tags ON health_events USING GIN(tags);
CREATE INDEX idx_semantic_correlations_user ON semantic_correlations(user_id, strength);
CREATE INDEX idx_pattern_insights_user ON pattern_insights(user_id, pattern_type, confidence_score DESC);

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_health_events_updated_at
    BEFORE UPDATE ON health_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
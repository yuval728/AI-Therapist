-- Performance Optimization Indexes for AI Therapist
-- This script adds indexes for frequently queried columns to improve performance

-- User-related queries (most common)
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_id ON therapy_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_logs_user_id ON memory_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_crisis_events_user_id ON crisis_events(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_user_id ON performance_metrics(user_id);

-- Session-related queries
CREATE INDEX IF NOT EXISTS idx_memory_logs_session_id ON memory_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_created ON therapy_sessions(user_id, created_at DESC);

-- Timestamp-based queries for pagination and ordering
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_created_at ON therapy_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_logs_created_at ON memory_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_logs_user_session_created ON memory_logs(user_id, session_id, created_at DESC);

-- Crisis detection queries
CREATE INDEX IF NOT EXISTS idx_crisis_events_created_at ON crisis_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_events_user_created ON crisis_events(user_id, created_at DESC);

-- Session status queries
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_status ON therapy_sessions(processing_status);
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_status ON therapy_sessions(user_id, processing_status);

-- Memory and document similarity searches (if using vector similarity)
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX IF NOT EXISTS idx_memory_logs_embedding ON memory_logs USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_emotion ON therapy_sessions(user_id, emotion);
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_user_crisis ON therapy_sessions(user_id, crisis_level);

-- Performance metrics queries
CREATE INDEX IF NOT EXISTS idx_performance_metrics_created_at ON performance_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events(created_at DESC);

-- Auth and session management
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Add partial indexes for active sessions (memory optimization)
CREATE INDEX IF NOT EXISTS idx_therapy_sessions_active ON therapy_sessions(user_id, updated_at DESC) 
  WHERE ended_at IS NULL;

-- Add expression indexes for JSON queries on preferences
CREATE INDEX IF NOT EXISTS idx_profiles_preferences_gin ON profiles USING gin (preferences);

-- Statistics for query planner
ANALYZE therapy_sessions;
ANALYZE memory_logs;
ANALYZE crisis_events;
ANALYZE documents;
ANALYZE profiles;
ANALYZE security_events;
ANALYZE performance_metrics;

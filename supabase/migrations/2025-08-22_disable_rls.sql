-- Disable RLS and drop policies across application tables

-- Drop policies (if they exist)
drop policy if exists "Users can view own profile" on profiles;
drop policy if exists "Users can update own profile" on profiles;

drop policy if exists "Users can manage own sessions" on therapy_sessions;

drop policy if exists "Users can manage own memory" on memory_logs;

drop policy if exists "Users can view own crisis events" on crisis_events;
drop policy if exists "System can insert crisis events" on crisis_events;

drop policy if exists "Users can manage own documents" on documents;

drop policy if exists "System can insert security events" on security_events;

drop policy if exists "System can insert metrics" on performance_metrics;

-- Disable RLS on all app tables
alter table if exists profiles disable row level security;
alter table if exists therapy_sessions disable row level security;
alter table if exists memory_logs disable row level security;
alter table if exists crisis_events disable row level security;
alter table if exists documents disable row level security;
alter table if exists security_events disable row level security;
alter table if exists performance_metrics disable row level security;

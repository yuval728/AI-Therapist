-- === Enable required extensions ===
create extension if not exists vector;
create extension if not exists "uuid-ossp";

-- === User Profile Table (links to Supabase Auth) ===
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  email text,
  preferences jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- === Therapy Sessions ===
create table if not exists therapy_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id text not null,
  emotion text,
  crisis_level text check (crisis_level in ('low', 'moderate', 'high', 'critical')),
  processing_status text check (processing_status in ('pending', 'in_progress', 'completed', 'failed')) default 'pending',
  session_summary text,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, session_id)
);

-- === Enhanced Short-Term Memory Logs ===
create table if not exists memory_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id text not null,
  role text check (role in ('user', 'assistant')) not null,
  content text not null,
  message_type text check (message_type in ('user_input', 'ai_response', 'system_message', 'journal_entry')) default 'user_input',
  timestamp timestamptz default current_timestamp,
  emotion text,
  is_crisis boolean default false,
  crisis_level text,
  mode text check (mode in ('chat', 'journal')),
  journal_entry text,
  attack text,
  message_length integer,
  token_count integer,
  metadata jsonb default '{}'
);

-- === Crisis Events Tracking ===
create table if not exists crisis_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id text not null,
  crisis_level text check (crisis_level in ('low', 'moderate', 'high', 'critical')) not null,
  content text not null,
  escalation_needed boolean default false,
  resolved boolean default false,
  response_provided text,
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  resolved_at timestamptz
);

-- === Long-Term Memory with Vector Embeddings ===
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  content text not null,
  content_type text check (content_type in ('journal', 'conversation', 'insight', 'memory')) default 'memory',
  metadata jsonb default '{}',
  embedding vector(768),  -- Google Gemini embedding dimension
  created_at timestamptz default now()
);

-- === Security Events Logging ===
create table if not exists security_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  event_type text not null,
  severity text check (severity in ('low', 'medium', 'high', 'critical')) default 'medium',
  content text,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- === Performance Metrics ===
create table if not exists performance_metrics (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  operation text not null,
  duration_ms float not null,
  success boolean default true,
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

-- === Enhanced RPC Function for Vector Search ===
create or replace function match_documents (
  user_id_param uuid,
  query_embedding vector(768),
  match_threshold float default 0.7,
  match_count int default 3
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <#> query_embedding) as similarity
  from documents
  where user_id = user_id_param
    and 1 - (embedding <#> query_embedding) > match_threshold
  order by embedding <#> query_embedding
  limit match_count;
$$;

-- === Indexes for Performance ===
create index if not exists idx_memory_logs_user_timestamp on memory_logs(user_id, timestamp desc);
create index if not exists idx_memory_logs_session on memory_logs(user_id, session_id, timestamp desc);
create index if not exists idx_therapy_sessions_user on therapy_sessions(user_id, created_at desc);
create index if not exists idx_crisis_events_user on crisis_events(user_id, created_at desc);
create index if not exists idx_documents_user on documents(user_id, created_at desc);
create index if not exists idx_security_events_user on security_events(user_id, created_at desc);
create index if not exists idx_performance_metrics_operation on performance_metrics(operation, created_at desc);

-- === Row Level Security (RLS) Policies ===
alter table profiles enable row level security;
alter table therapy_sessions enable row level security;
alter table memory_logs enable row level security;
alter table crisis_events enable row level security;
alter table documents enable row level security;
alter table security_events enable row level security;
alter table performance_metrics enable row level security;

-- Profiles policies
create policy "Users can view own profile" on profiles for select using (auth.uid() = id);
create policy "Users can update own profile" on profiles for update using (auth.uid() = id);

-- Therapy sessions policies
create policy "Users can manage own sessions" on therapy_sessions for all using (auth.uid() = user_id);

-- Memory logs policies
create policy "Users can manage own memory" on memory_logs for all using (auth.uid() = user_id);

-- Crisis events policies
create policy "Users can view own crisis events" on crisis_events for select using (auth.uid() = user_id);
create policy "System can insert crisis events" on crisis_events for insert with check (true);

-- Documents policies
create policy "Users can manage own documents" on documents for all using (auth.uid() = user_id);

-- Security events policies (admin access only)
create policy "System can insert security events" on security_events for insert with check (true);

-- Performance metrics policies (system access)
create policy "System can insert metrics" on performance_metrics for insert with check (true);

-- === Triggers for updated_at ===
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger update_profiles_updated_at before update on profiles
  for each row execute function update_updated_at_column();

create trigger update_therapy_sessions_updated_at before update on therapy_sessions
  for each row execute function update_updated_at_column();
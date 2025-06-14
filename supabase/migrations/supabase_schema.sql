-- === Enable pgvector for vector search ===
create extension if not exists vector;

-- === User Profile Table (links to Supabase Auth) ===
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  created_at timestamptz default now()
);

-- === Short-Term Memory Logs ===
create table if not exists memory_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  role text check (role in ('user', 'assistant')) not null,
  content text not null,
  timestamp timestamptz default current_timestamp,
  emotion text,
  is_crisis boolean,
  mode text check (mode in ('chat', 'journal')),
  journal_entry text,
  attack text
);

-- === Long-Term Memory with Vector Embeddings ===
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  content text not null,
  metadata jsonb,
  embedding vector(1536)  -- Adjust dimension for your embedding model
);

-- === RPC Function for Vector Search ===
create or replace function match_documents (
  filter jsonb,
  query_embedding vector
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
  where metadata->>'user_id' = user_id::text
  order by embedding <#> query_embedding
  limit 3;
$$;
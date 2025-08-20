-- Migration: Ensure match_documents RPC exists with expected signature
-- Creates or replaces public.match_documents(user_id_param uuid, query_embedding vector(768), match_threshold float, match_count int)

create or replace function public.match_documents (
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
  from public.documents
  where user_id = user_id_param
    and 1 - (embedding <#> query_embedding) > match_threshold
  order by embedding <#> query_embedding
  limit match_count;
$$;

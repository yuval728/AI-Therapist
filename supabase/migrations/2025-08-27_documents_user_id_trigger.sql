-- Populate documents.user_id from metadata->>'user_id' to satisfy NOT NULL and align with vector-store inserts

create or replace function documents_set_user_id_from_metadata()
returns trigger as $$
begin
  -- If user_id column is null but metadata contains a user_id, set it
  if new.user_id is null and new.metadata ? 'user_id' then
    begin
      new.user_id := (new.metadata->>'user_id')::uuid;
    exception when others then
      -- Ignore cast errors; let constraints/policies handle them
      null;
    end;
  end if;
  return new;
end;
$$ language plpgsql;

-- Attach trigger to documents table for insert and update
 drop trigger if exists trg_documents_set_user_id on documents;
create trigger trg_documents_set_user_id
  before insert or update on documents
  for each row
  execute function documents_set_user_id_from_metadata();

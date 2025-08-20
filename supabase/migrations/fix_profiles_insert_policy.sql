-- Fix profiles table RLS policy to allow INSERT during signup
-- This allows users to create their own profile during registration

-- Add INSERT policy for profiles table
create policy "Users can insert own profile" on profiles 
  for insert 
  with check (auth.uid() = id);

-- Ensure the policy is properly applied
alter table profiles force row level security;

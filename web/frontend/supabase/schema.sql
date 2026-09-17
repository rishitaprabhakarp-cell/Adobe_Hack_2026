-- GEOReady users + sites in Supabase Postgres.
-- Run this once in the SQL editor.

-- Auth lives in auth.users (email/password). This table is the app profile.
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "Users read own profile" on public.profiles;
create policy "Users read own profile"
  on public.profiles for select
  using (auth.uid() = id);

drop policy if exists "Users insert own profile" on public.profiles;
create policy "Users insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

drop policy if exists "Users update own profile" on public.profiles;
create policy "Users update own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'name', '')
  )
  on conflict (id) do update
    set email = excluded.email,
        name = excluded.name,
        updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Existing auth users get a profile row.
insert into public.profiles (id, email, name)
select
  id,
  email,
  coalesce(raw_user_meta_data->>'name', '')
from auth.users
on conflict (id) do nothing;

create table if not exists public.audits (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  job_id text,
  domain text not null,
  url text,
  status text not null default 'done',
  score integer,
  findings integer,
  report jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, domain)
);

create index if not exists audits_user_id_idx on public.audits (user_id);
create index if not exists audits_job_id_idx on public.audits (job_id);

alter table public.audits enable row level security;

drop policy if exists "Users read own audits" on public.audits;
create policy "Users read own audits"
  on public.audits for select
  using (auth.uid() = user_id);

drop policy if exists "Users insert own audits" on public.audits;
create policy "Users insert own audits"
  on public.audits for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users update own audits" on public.audits;
create policy "Users update own audits"
  on public.audits for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users delete own audits" on public.audits;
create policy "Users delete own audits"
  on public.audits for delete
  using (auth.uid() = user_id);

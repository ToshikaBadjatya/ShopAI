-- User info memory: what ShopAI remembers about a shopper between sessions.
-- One row per user, owned by that user through RLS.
--
-- Apply by pasting into the Supabase SQL editor (Dashboard -> SQL Editor).

create table if not exists public.user_memory (
    user_id            uuid primary key references auth.users (id) on delete cascade,

    -- Who they are, in styling terms
    culture_summary    text        not null default '',
    height             text        not null default '',
    body_type          text        not null default '',   -- curvy, wavy, oval, ...

    -- Colour tone: how colour behaves against them
    skin_tone          text        not null default '',    -- fair, light, medium, olive, deep
    undertone          text        not null default '',    -- warm, cool, neutral
    color_season       text        not null default '',    -- spring, summer, autumn, winter
    contrast_level     text        not null default '',    -- high, medium, low
    colors_to_avoid    text[]      not null default '{}',

    -- What works for them
    colors_that_work   text[]      not null default '{}',
    preferred_fabrics  text[]      not null default '{}',
    preferred_pieces   text[]      not null default '{}',  -- outfit pieces they like
    preferred_styles   text[]      not null default '{}',

    -- Anything not worth its own column yet
    details            jsonb       not null default '{}'::jsonb,

    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

comment on table public.user_memory is
    'Persistent per-user styling memory. One row per user; RLS confines each user to their own.';

-- Keep updated_at honest without the client having to remember.
create or replace function public.touch_user_memory_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists user_memory_touch_updated_at on public.user_memory;
create trigger user_memory_touch_updated_at
    before update on public.user_memory
    for each row execute function public.touch_user_memory_updated_at();

-- Row level security: a user reaches their own row and no other.
alter table public.user_memory enable row level security;

drop policy if exists "user_memory_select_own" on public.user_memory;
create policy "user_memory_select_own" on public.user_memory
    for select using (auth.uid() = user_id);

drop policy if exists "user_memory_insert_own" on public.user_memory;
create policy "user_memory_insert_own" on public.user_memory
    for insert with check (auth.uid() = user_id);

drop policy if exists "user_memory_update_own" on public.user_memory;
create policy "user_memory_update_own" on public.user_memory
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "user_memory_delete_own" on public.user_memory;
create policy "user_memory_delete_own" on public.user_memory
    for delete using (auth.uid() = user_id);

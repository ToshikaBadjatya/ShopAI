-- Conversation turns: the verbatim transcript of one run.
-- Mem0 holds the summary; this holds what was actually said.
--
-- Apply by pasting into the Supabase SQL editor (Dashboard -> SQL Editor).

create table if not exists public.conversation (
    id         uuid        primary key default gen_random_uuid(),
    run_id     uuid        not null,
    user_id    uuid        not null references auth.users (id) on delete cascade,
    sender     text        not null check (sender in ('user', 'agent')),
    message    text        not null,
    created_at timestamptz not null default now()
);

comment on table public.conversation is
    'Turn-by-turn transcript, one row per message. Clarity scoring reads the user turns.';

-- Every read is "this run's turns, in order".
create index if not exists conversation_run_created_idx
    on public.conversation (run_id, created_at);

alter table public.conversation enable row level security;

drop policy if exists "conversation_select_own" on public.conversation;
create policy "conversation_select_own" on public.conversation
    for select using (auth.uid() = user_id);

drop policy if exists "conversation_insert_own" on public.conversation;
create policy "conversation_insert_own" on public.conversation
    for insert with check (auth.uid() = user_id);

drop policy if exists "conversation_update_own" on public.conversation;
create policy "conversation_update_own" on public.conversation
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "conversation_delete_own" on public.conversation;
create policy "conversation_delete_own" on public.conversation
    for delete using (auth.uid() = user_id);

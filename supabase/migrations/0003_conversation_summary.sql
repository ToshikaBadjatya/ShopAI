-- Rolling summary of one run, so a long conversation can be carried without its
-- whole transcript. The verbatim turns stay in public.conversation; this row is
-- derived from them and is never used as evidence.
--
-- Apply by pasting into the Supabase SQL editor (Dashboard -> SQL Editor).

create table if not exists public.conversation_summary (
    run_id           uuid        primary key,
    user_id          uuid        not null references auth.users (id) on delete cascade,
    summary          text        not null default '',
    through_at       timestamptz,   -- created_at of the last turn folded into `summary`
    learned_through  timestamptz,   -- created_at of the last turn the profile learner has read
    updated_at       timestamptz not null default now()
);

comment on table public.conversation_summary is
    'One row per run: the rolling summary and how far summarising and profile learning have got.';

create or replace function public.touch_conversation_summary_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists conversation_summary_touch_updated_at on public.conversation_summary;
create trigger conversation_summary_touch_updated_at
    before update on public.conversation_summary
    for each row execute function public.touch_conversation_summary_updated_at();

alter table public.conversation_summary enable row level security;

drop policy if exists "conversation_summary_select_own" on public.conversation_summary;
create policy "conversation_summary_select_own" on public.conversation_summary
    for select using (auth.uid() = user_id);

drop policy if exists "conversation_summary_insert_own" on public.conversation_summary;
create policy "conversation_summary_insert_own" on public.conversation_summary
    for insert with check (auth.uid() = user_id);

drop policy if exists "conversation_summary_update_own" on public.conversation_summary;
create policy "conversation_summary_update_own" on public.conversation_summary
    for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "conversation_summary_delete_own" on public.conversation_summary;
create policy "conversation_summary_delete_own" on public.conversation_summary
    for delete using (auth.uid() = user_id);

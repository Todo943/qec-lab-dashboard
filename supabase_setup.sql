-- QEC Lab shared results. Run once in YOUR Supabase project SQL editor.
-- Anyone who can access the public app can read and insert experimental data.
-- Unauthenticated clients CANNOT update or delete existing rows.
-- Never use a service_role/secret key in public client code.

create table if not exists public.qec_experiments (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  label text not null check (char_length(label) between 2 and 70),
  device text not null check (char_length(device) between 1 and 40 and device ~ '^[a-zA-Z0-9 _.-]+$'),
  distance smallint not null check (distance between 1 and 31),
  basis text not null check (basis in ('X', 'Z')),
  kind text not null check (kind in ('aggregate', 'events')),
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object' and pg_column_size(metadata) < 4096),
  payload jsonb not null check (
    jsonb_typeof(payload) = 'object'
    and pg_column_size(payload) <= 2000000
    and (
      (kind = 'aggregate' and (payload ? 'hardware' or payload ? 'simulation'))
      or (kind = 'events' and payload ? 'det_events')
    )
  )
);

create index if not exists qec_experiments_created_idx
on public.qec_experiments (created_at desc);

alter table public.qec_experiments enable row level security;

-- Explicitly limit the browser role. Service/owner privileges are unaffected.
revoke all on table public.qec_experiments from public, anon, authenticated;
grant select on table public.qec_experiments to anon;
grant insert (label,device,distance,basis,kind,metadata,payload)
  on table public.qec_experiments to anon;

drop policy if exists "qec_public_read" on public.qec_experiments;
create policy "qec_public_read" on public.qec_experiments
  for select to anon using (true);

drop policy if exists "qec_guest_create_only" on public.qec_experiments;
create policy "qec_guest_create_only" on public.qec_experiments
  for insert to anon with check (
    char_length(label) between 2 and 70
    and char_length(device) between 1 and 40
    and distance between 1 and 31
    and kind in ('aggregate','events')
  );

-- Intentionally NO anonymous UPDATE or DELETE grants/policies.
-- Important: This is public, unauthenticated insertion. See README security notes.

-- QEC Lab v2: support circuit-layout JSON in addition to aggregate and detector data.
-- Run ONCE in your existing Supabase project's SQL Editor, after supabase_setup.sql.
-- Existing experiments and access credentials are preserved.
BEGIN;
ALTER TABLE public.qec_experiments DROP CONSTRAINT IF EXISTS qec_experiments_kind_check;
ALTER TABLE public.qec_experiments ADD CONSTRAINT qec_experiments_kind_check
  CHECK (kind IN ('aggregate','events','circuit'));
ALTER TABLE public.qec_experiments DROP CONSTRAINT IF EXISTS qec_experiments_payload_check;
ALTER TABLE public.qec_experiments ADD CONSTRAINT qec_experiments_payload_check CHECK (
  jsonb_typeof(payload) = 'object' AND pg_column_size(payload) <= 2000000
  AND (
    (kind='aggregate' AND (payload ? 'hardware' OR payload ? 'simulation'))
    OR (kind='events' AND payload ? 'det_events')
    OR (kind='circuit' AND payload ? 'qubits')
  )
);
DROP POLICY IF EXISTS "qec_guest_create_only" ON public.qec_experiments;
CREATE POLICY "qec_guest_create_only" ON public.qec_experiments
  FOR INSERT TO anon WITH CHECK (
    char_length(label) BETWEEN 2 AND 70
    AND char_length(device) BETWEEN 1 AND 40
    AND distance BETWEEN 1 AND 31
    AND basis IN ('X', 'Z')
    AND kind IN ('aggregate','events','circuit')
  );
COMMIT;
-- NOTE: public anonymous INSERT is still enabled by design. See SECURITY.md.

-- journal_inference: per-entry system inferences (replaceable, non-authoritative)
CREATE TABLE IF NOT EXISTS journal_inference (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id uuid NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
  container text NOT NULL CHECK (container IN ('affect','cognition','somatic','vitality','context')),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  confidence numeric,
  inference_type text NOT NULL CHECK (inference_type IN ('interpretive','structural','narrative')),
  source text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS journal_inference_entry_idx ON journal_inference(entry_id);
CREATE INDEX IF NOT EXISTS journal_inference_container_idx ON journal_inference(container);
CREATE INDEX IF NOT EXISTS journal_inference_type_idx ON journal_inference(inference_type);

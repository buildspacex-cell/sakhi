-- Build 43 helper: ensure personal_model has emotion column for baseline pulls.
ALTER TABLE personal_model
    ADD COLUMN IF NOT EXISTS emotion TEXT;


-- Build 33 follow-up: enforce uniqueness for planned_items (person_id, origin_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'planned_items_person_origin_key'
    ) THEN
        ALTER TABLE planned_items
            ADD CONSTRAINT planned_items_person_origin_key
            UNIQUE (person_id, origin_id);
    END IF;
END;
$$;


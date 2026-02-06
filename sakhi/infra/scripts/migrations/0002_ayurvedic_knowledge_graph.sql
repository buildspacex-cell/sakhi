-- Ayurvedic Knowledge Graph with Citation Support
-- Phase 1: Foundation for validated Ayurvedic knowledge from primary sources
-- Sources: Charaka Samhita, Ashtanga Hridaya, Sushruta Samhita, Bhavaprakasha

-- ============================================================================
-- KNOWLEDGE GRAPH NODES
-- ============================================================================

CREATE TABLE IF NOT EXISTS ay_nodes (
    id BIGSERIAL PRIMARY KEY,

    -- Core identity
    kind TEXT NOT NULL,                    -- dosha, food, herb, practice, symptom, season, time_window, quality, rasa, etc.
    name TEXT NOT NULL,                    -- English identifier (e.g., "ginger", "vata")
    name_sanskrit TEXT,                    -- Sanskrit name (e.g., "shunti", "vayu")
    display_name TEXT,                     -- User-facing name

    -- Properties (flexible JSONB for kind-specific attributes)
    attrs JSONB DEFAULT '{}'::jsonb,

    -- Citation & Provenance
    citations JSONB DEFAULT '[]'::jsonb,   -- [{source, chapter, shloka, text, translator}]
    confidence FLOAT DEFAULT 1.0,          -- 1.0=direct quote, 0.8=clear inference, 0.6=interpretation
    extraction_method TEXT DEFAULT 'manual', -- manual, llm_extract, llm_validated, scholarly
    validated_at TIMESTAMPTZ,
    validated_by TEXT,                     -- 'llm:claude-3', 'human:scholar_name', etc.

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint on kind + name
CREATE UNIQUE INDEX IF NOT EXISTS ay_nodes_kind_name_idx
ON ay_nodes(kind, name);

-- Index for Sanskrit name lookups
CREATE INDEX IF NOT EXISTS ay_nodes_name_sanskrit_idx
ON ay_nodes(name_sanskrit) WHERE name_sanskrit IS NOT NULL;

-- Index for kind queries
CREATE INDEX IF NOT EXISTS ay_nodes_kind_idx ON ay_nodes(kind);

-- ============================================================================
-- KNOWLEDGE GRAPH EDGES
-- ============================================================================

CREATE TABLE IF NOT EXISTS ay_edges (
    id BIGSERIAL PRIMARY KEY,

    -- Relationship
    src BIGINT NOT NULL REFERENCES ay_nodes(id) ON DELETE CASCADE,
    dst BIGINT NOT NULL REFERENCES ay_nodes(id) ON DELETE CASCADE,
    rel TEXT NOT NULL,                     -- PACIFIES, AGGRAVATES, INDICATES, HAS_QUALITY, etc.

    -- Strength & Context
    weight FLOAT DEFAULT 1.0,              -- Base relationship strength
    context JSONB DEFAULT '{}'::jsonb,     -- Conditions: {season, time, constitution, etc.}

    -- Citation & Provenance
    citations JSONB DEFAULT '[]'::jsonb,   -- Source citations for this relationship
    confidence FLOAT DEFAULT 1.0,
    extraction_method TEXT DEFAULT 'manual',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for graph traversal
CREATE INDEX IF NOT EXISTS ay_edges_src_idx ON ay_edges(src);
CREATE INDEX IF NOT EXISTS ay_edges_dst_idx ON ay_edges(dst);
CREATE INDEX IF NOT EXISTS ay_edges_rel_idx ON ay_edges(rel);
CREATE INDEX IF NOT EXISTS ay_edges_src_rel_idx ON ay_edges(src, rel);

-- Prevent duplicate edges
CREATE UNIQUE INDEX IF NOT EXISTS ay_edges_unique_idx
ON ay_edges(src, dst, rel) WHERE context = '{}'::jsonb;

-- ============================================================================
-- SOURCE TEXT REGISTRY
-- ============================================================================

CREATE TABLE IF NOT EXISTS ay_sources (
    id SERIAL PRIMARY KEY,

    -- Source identification
    code TEXT NOT NULL UNIQUE,             -- charaka_samhita, ashtanga_hridaya, etc.
    title TEXT NOT NULL,
    title_sanskrit TEXT,
    author TEXT,
    period TEXT,                           -- "~200 BCE - 200 CE"

    -- Structure
    sections JSONB DEFAULT '[]'::jsonb,    -- [{code, name, description}]

    -- Metadata
    translation_used TEXT,                 -- Which translation we're referencing
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert known sources
INSERT INTO ay_sources (code, title, title_sanskrit, author, period, sections, translation_used) VALUES
(
    'charaka_samhita',
    'Charaka Samhita',
    'चरक संहिता',
    'Charaka (compiled by Dridhabala)',
    '~200 BCE - 200 CE',
    '[
        {"code": "sutrasthana", "name": "Sutra Sthana", "chapters": 30, "focus": "General principles, lifestyle, diet"},
        {"code": "nidanasthana", "name": "Nidana Sthana", "chapters": 8, "focus": "Pathology, diagnosis"},
        {"code": "vimanasthana", "name": "Vimana Sthana", "chapters": 8, "focus": "Specific determination of disease"},
        {"code": "sharirasthana", "name": "Sharira Sthana", "chapters": 8, "focus": "Anatomy, embryology"},
        {"code": "indriyasthana", "name": "Indriya Sthana", "chapters": 12, "focus": "Prognosis"},
        {"code": "chikitsasthana", "name": "Chikitsa Sthana", "chapters": 30, "focus": "Treatment"},
        {"code": "kalpasthana", "name": "Kalpa Sthana", "chapters": 12, "focus": "Pharmacy"},
        {"code": "siddhisthana", "name": "Siddhi Sthana", "chapters": 12, "focus": "Successful treatment"}
    ]'::jsonb,
    'P.V. Sharma translation (Chaukhamba)'
),
(
    'ashtanga_hridaya',
    'Ashtanga Hridaya',
    'अष्टाङ्गहृदय',
    'Vagbhata',
    '~600 CE',
    '[
        {"code": "sutrasthana", "name": "Sutra Sthana", "chapters": 30, "focus": "Daily routine, seasonal regimen, diet"},
        {"code": "sharirasthana", "name": "Sharira Sthana", "chapters": 6, "focus": "Anatomy, physiology"},
        {"code": "nidanasthana", "name": "Nidana Sthana", "chapters": 16, "focus": "Etiology, pathology"},
        {"code": "chikitsasthana", "name": "Chikitsa Sthana", "chapters": 22, "focus": "Treatment"},
        {"code": "kalpasthana", "name": "Kalpa Sthana", "chapters": 6, "focus": "Toxicology"},
        {"code": "uttarasthana", "name": "Uttara Sthana", "chapters": 40, "focus": "Additional treatments"}
    ]'::jsonb,
    'K.R. Srikantha Murthy translation'
),
(
    'sushruta_samhita',
    'Sushruta Samhita',
    'सुश्रुत संहिता',
    'Sushruta',
    '~600 BCE',
    '[
        {"code": "sutrasthana", "name": "Sutra Sthana", "chapters": 46, "focus": "General principles"},
        {"code": "nidanasthana", "name": "Nidana Sthana", "chapters": 16, "focus": "Diagnosis"},
        {"code": "sharirasthana", "name": "Sharira Sthana", "chapters": 10, "focus": "Anatomy"},
        {"code": "chikitsasthana", "name": "Chikitsa Sthana", "chapters": 40, "focus": "Treatment"},
        {"code": "kalpasthana", "name": "Kalpa Sthana", "chapters": 8, "focus": "Toxicology"},
        {"code": "uttaratantra", "name": "Uttara Tantra", "chapters": 66, "focus": "Additional topics"}
    ]'::jsonb,
    'G.D. Singhal translation'
),
(
    'bhavaprakasha',
    'Bhavaprakasha',
    'भावप्रकाश',
    'Bhavamishra',
    '~1550 CE',
    '[
        {"code": "purva_khanda", "name": "Purva Khanda", "chapters": 7, "focus": "General principles"},
        {"code": "madhya_khanda", "name": "Madhya Khanda (Nighantu)", "chapters": 1, "focus": "Materia medica - foods, herbs"},
        {"code": "uttara_khanda", "name": "Uttara Khanda", "chapters": 1, "focus": "Diseases and treatment"}
    ]'::jsonb,
    'K.C. Chunekar translation'
)
ON CONFLICT (code) DO NOTHING;

-- ============================================================================
-- VALIDATION LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS ay_validation_log (
    id BIGSERIAL PRIMARY KEY,

    -- What was validated
    node_id BIGINT REFERENCES ay_nodes(id) ON DELETE CASCADE,
    edge_id BIGINT REFERENCES ay_edges(id) ON DELETE CASCADE,

    -- Validation result
    status TEXT NOT NULL,                  -- validated, corrected, flagged, rejected
    original_data JSONB,                   -- Data before validation
    corrected_data JSONB,                  -- Data after correction (if any)

    -- Reasoning
    llm_reasoning TEXT,                    -- LLM's explanation
    citations_found JSONB DEFAULT '[]',    -- Citations discovered during validation
    confidence_score FLOAT,

    -- Flags
    contradicts_source BOOLEAN DEFAULT FALSE,
    needs_review BOOLEAN DEFAULT FALSE,
    review_notes TEXT,

    -- Metadata
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    validated_by TEXT                      -- 'llm:claude-3-opus', 'human:name', etc.
);

CREATE INDEX IF NOT EXISTS ay_validation_log_node_idx ON ay_validation_log(node_id);
CREATE INDEX IF NOT EXISTS ay_validation_log_status_idx ON ay_validation_log(status);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get node by kind and name
CREATE OR REPLACE FUNCTION ay_get_node(p_kind TEXT, p_name TEXT)
RETURNS TABLE(id BIGINT, attrs JSONB, citations JSONB, confidence FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT n.id, n.attrs, n.citations, n.confidence
    FROM ay_nodes n
    WHERE n.kind = p_kind AND n.name = p_name;
END;
$$ LANGUAGE plpgsql;

-- Get all edges from a node
CREATE OR REPLACE FUNCTION ay_get_edges_from(p_node_id BIGINT, p_rel TEXT DEFAULT NULL)
RETURNS TABLE(dst_id BIGINT, dst_kind TEXT, dst_name TEXT, rel TEXT, weight FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT e.dst, n.kind, n.name, e.rel, e.weight
    FROM ay_edges e
    JOIN ay_nodes n ON e.dst = n.id
    WHERE e.src = p_node_id
      AND (p_rel IS NULL OR e.rel = p_rel);
END;
$$ LANGUAGE plpgsql;

-- Get foods that pacify a dosha
CREATE OR REPLACE FUNCTION ay_foods_for_dosha(p_dosha TEXT, p_relation TEXT DEFAULT 'PACIFIES')
RETURNS TABLE(food_name TEXT, food_attrs JSONB, weight FLOAT, citations JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT f.name, f.attrs, e.weight, f.citations
    FROM ay_nodes d
    JOIN ay_edges e ON e.dst = d.id
    JOIN ay_nodes f ON e.src = f.id
    WHERE d.kind = 'dosha'
      AND d.name = p_dosha
      AND f.kind = 'food'
      AND e.rel = p_relation
    ORDER BY e.weight DESC;
END;
$$ LANGUAGE plpgsql;

-- Get practices for a dosha
CREATE OR REPLACE FUNCTION ay_practices_for_dosha(p_dosha TEXT, p_relation TEXT DEFAULT 'PACIFIES')
RETURNS TABLE(practice_name TEXT, practice_attrs JSONB, weight FLOAT, citations JSONB) AS $$
BEGIN
    RETURN QUERY
    SELECT p.name, p.attrs, e.weight, p.citations
    FROM ay_nodes d
    JOIN ay_edges e ON e.dst = d.id
    JOIN ay_nodes p ON e.src = p.id
    WHERE d.kind = 'dosha'
      AND d.name = p_dosha
      AND p.kind = 'practice'
      AND e.rel = p_relation
    ORDER BY e.weight DESC;
END;
$$ LANGUAGE plpgsql;

-- Get symptoms indicating dosha imbalance
CREATE OR REPLACE FUNCTION ay_symptoms_for_dosha(p_dosha TEXT)
RETURNS TABLE(symptom_name TEXT, symptom_attrs JSONB, weight FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT s.name, s.attrs, e.weight
    FROM ay_nodes d
    JOIN ay_edges e ON e.dst = d.id
    JOIN ay_nodes s ON e.src = s.id
    WHERE d.kind = 'dosha'
      AND d.name = p_dosha
      AND s.kind = 'symptom'
      AND e.rel = 'INDICATES'
    ORDER BY e.weight DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE ay_nodes IS 'Ayurvedic knowledge graph nodes - doshas, foods, herbs, practices, symptoms, etc.';
COMMENT ON TABLE ay_edges IS 'Relationships between Ayurvedic concepts - PACIFIES, AGGRAVATES, INDICATES, etc.';
COMMENT ON TABLE ay_sources IS 'Registry of Ayurvedic source texts used for citations';
COMMENT ON TABLE ay_validation_log IS 'Log of LLM and human validation of knowledge graph entries';

COMMENT ON COLUMN ay_nodes.citations IS 'Array of citations: [{source, chapter, shloka, text}]';
COMMENT ON COLUMN ay_nodes.confidence IS '1.0=direct quote, 0.8=clear inference, 0.6=interpretation';
COMMENT ON COLUMN ay_nodes.extraction_method IS 'How this node was created: manual, llm_extract, llm_validated, scholarly';

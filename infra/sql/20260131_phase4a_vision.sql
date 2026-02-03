-- =============================================================================
-- Phase 4a: Vision & Multi-modal Foundation
-- =============================================================================
-- Enables Sakhi to understand images, screenshots, and documents.
--
-- Capabilities:
-- - Accept images in conversations
-- - Analyze screenshots and documents
-- - Extract text and meaning from visual content
-- - Store visual context for memory
-- =============================================================================

-- =============================================================================
-- 1. Media Attachments Table
-- =============================================================================
-- Stores references to uploaded images, documents, screenshots

CREATE TABLE IF NOT EXISTS media_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,

    -- Media info
    media_type TEXT NOT NULL,  -- 'image', 'document', 'screenshot', 'photo'
    mime_type TEXT NOT NULL,   -- 'image/png', 'image/jpeg', 'application/pdf'
    filename TEXT,
    file_size_bytes INTEGER,

    -- Storage
    storage_provider TEXT NOT NULL DEFAULT 'local',  -- 'local', 's3', 'gcs'
    storage_path TEXT NOT NULL,                       -- Path or URL to file
    thumbnail_path TEXT,                              -- Optional thumbnail

    -- Extracted content
    extracted_text TEXT,           -- OCR or parsed text
    description TEXT,              -- AI-generated description
    analysis JSONB DEFAULT '{}',   -- Structured analysis
    /* Analysis structure:
    {
        "objects": ["laptop", "coffee cup", "notebook"],
        "text_detected": true,
        "document_type": "receipt",
        "sentiment": "neutral",
        "key_information": {
            "total": "$45.99",
            "date": "2024-01-15",
            "vendor": "Amazon"
        },
        "tags": ["work", "expense", "shopping"]
    }
    */

    -- Context
    source TEXT,                   -- 'upload', 'camera', 'screenshot', 'share'
    context TEXT,                  -- User's note about what this is

    -- Processing status
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'ready', 'failed'
    processed_at TIMESTAMPTZ,
    error_message TEXT,

    -- Metadata
    width INTEGER,
    height INTEGER,
    duration_seconds FLOAT,        -- For video/audio (future)
    metadata JSONB DEFAULT '{}',   -- EXIF, etc.

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_media_person ON media_attachments(person_id);
CREATE INDEX idx_media_type ON media_attachments(media_type);
CREATE INDEX idx_media_status ON media_attachments(status);
CREATE INDEX idx_media_created ON media_attachments(created_at DESC);

-- =============================================================================
-- 2. Conversation Media Links
-- =============================================================================
-- Links media to specific conversation turns

CREATE TABLE IF NOT EXISTS conversation_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media_attachments(id) ON DELETE CASCADE,

    -- Link to conversation
    session_id TEXT,               -- Conversation session
    entry_id UUID,                 -- Journal entry if applicable
    turn_index INTEGER,            -- Which turn in conversation

    -- How it was used
    role TEXT NOT NULL DEFAULT 'user',  -- 'user' (sent by user) or 'assistant' (generated)
    purpose TEXT,                  -- 'question', 'context', 'reference', 'analysis'

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_conv_media_session ON conversation_media(session_id);
CREATE INDEX idx_conv_media_entry ON conversation_media(entry_id);
CREATE INDEX idx_conv_media_media ON conversation_media(media_id);

-- =============================================================================
-- 3. Vision Memory Table
-- =============================================================================
-- Stores learned information from visual content

CREATE TABLE IF NOT EXISTS vision_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    media_id UUID REFERENCES media_attachments(id) ON DELETE SET NULL,

    -- What was learned
    memory_type TEXT NOT NULL,     -- 'place', 'person', 'object', 'document', 'preference'
    subject TEXT NOT NULL,         -- What/who this is about
    learned_facts JSONB DEFAULT '[]',
    /* Example:
    [
        {"fact": "User's home office has dual monitors", "confidence": 0.9},
        {"fact": "User prefers dark mode interfaces", "confidence": 0.8}
    ]
    */

    -- Embeddings for similarity search
    embedding vector(1536),

    -- Context
    source_description TEXT,       -- How this was learned
    confidence FLOAT DEFAULT 0.5,

    -- Lifecycle
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at TIMESTAMPTZ DEFAULT now(),
    times_seen INTEGER DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_vision_memory_person ON vision_memory(person_id);
CREATE INDEX idx_vision_memory_type ON vision_memory(memory_type);
CREATE INDEX idx_vision_memory_subject ON vision_memory(subject);

-- =============================================================================
-- 4. Document Store
-- =============================================================================
-- For parsed documents (PDFs, etc.)

CREATE TABLE IF NOT EXISTS parsed_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID NOT NULL REFERENCES media_attachments(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,

    -- Document info
    document_type TEXT,            -- 'receipt', 'invoice', 'contract', 'note', 'article'
    title TEXT,

    -- Content
    full_text TEXT,
    pages JSONB DEFAULT '[]',      -- Per-page content
    /* Pages structure:
    [
        {"page": 1, "text": "...", "tables": [...], "images": [...]},
        {"page": 2, "text": "...", "tables": [...], "images": [...]}
    ]
    */

    -- Structured extraction
    extracted_data JSONB DEFAULT '{}',
    /* For receipts:
    {
        "vendor": "Amazon",
        "date": "2024-01-15",
        "items": [{"name": "...", "price": 10.99}],
        "total": 45.99,
        "payment_method": "Visa ****1234"
    }
    */

    -- Search
    search_vector tsvector,
    embedding vector(1536),

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_parsed_docs_person ON parsed_documents(person_id);
CREATE INDEX idx_parsed_docs_type ON parsed_documents(document_type);
CREATE INDEX idx_parsed_docs_search ON parsed_documents USING GIN(search_vector);

-- Update search vector trigger
CREATE OR REPLACE FUNCTION update_parsed_doc_search()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.full_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_parsed_doc_search
BEFORE INSERT OR UPDATE ON parsed_documents
FOR EACH ROW EXECUTE FUNCTION update_parsed_doc_search();

-- =============================================================================
-- 5. Visual Context for Conversations
-- =============================================================================
-- Quick lookup of visual context for current conversation

CREATE TABLE IF NOT EXISTS visual_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    session_id TEXT NOT NULL,

    -- Current visual context
    active_media JSONB DEFAULT '[]',  -- List of media_ids currently relevant
    /* Structure:
    [
        {"media_id": "...", "description": "Screenshot of error", "relevance": 0.9},
        {"media_id": "...", "description": "Previous screenshot", "relevance": 0.5}
    ]
    */

    -- Accumulated understanding
    visual_summary TEXT,           -- Summary of what's been shown
    objects_mentioned JSONB DEFAULT '[]',
    people_mentioned JSONB DEFAULT '[]',

    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(person_id, session_id)
);

CREATE INDEX idx_visual_ctx_session ON visual_context(session_id);

-- =============================================================================
-- 6. Helper Functions
-- =============================================================================

-- Get recent media for a person
CREATE OR REPLACE FUNCTION get_recent_media(
    p_person_id TEXT,
    p_limit INTEGER DEFAULT 10,
    p_media_type TEXT DEFAULT NULL
)
RETURNS SETOF media_attachments AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM media_attachments
    WHERE person_id = p_person_id
      AND status = 'ready'
      AND (p_media_type IS NULL OR media_type = p_media_type)
    ORDER BY created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Get media for a conversation session
CREATE OR REPLACE FUNCTION get_session_media(p_session_id TEXT)
RETURNS TABLE (
    media_id UUID,
    media_type TEXT,
    description TEXT,
    extracted_text TEXT,
    analysis JSONB,
    turn_index INTEGER,
    role TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id as media_id,
        m.media_type,
        m.description,
        m.extracted_text,
        m.analysis,
        cm.turn_index,
        cm.role
    FROM media_attachments m
    JOIN conversation_media cm ON cm.media_id = m.id
    WHERE cm.session_id = p_session_id
    ORDER BY cm.turn_index;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 7. Journal Entry Media Links
-- =============================================================================
-- Links media directly to journal entries for memory and recall

CREATE TABLE IF NOT EXISTS journal_entry_media (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL,  -- References journal_entries(id)
    media_id UUID NOT NULL REFERENCES media_attachments(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,

    -- How media relates to the entry
    relationship TEXT DEFAULT 'attachment',  -- 'attachment', 'context', 'evidence', 'memory_trigger'
    caption TEXT,                            -- User's description of this media for this entry
    relevance_score FLOAT DEFAULT 1.0,       -- How relevant to the entry content

    -- For recall
    searchable_text TEXT,                    -- Combined text for search (description + extracted_text + caption)

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_journal_media_entry ON journal_entry_media(entry_id);
CREATE INDEX idx_journal_media_person ON journal_entry_media(person_id);
CREATE INDEX idx_journal_media_media ON journal_entry_media(media_id);

-- =============================================================================
-- 8. Memory Short-Term Media Links
-- =============================================================================
-- Links media to short-term memory for recall

CREATE TABLE IF NOT EXISTS memory_media_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID NOT NULL,  -- References memory_short_term(id) or memory_long_term(id)
    media_id UUID NOT NULL REFERENCES media_attachments(id) ON DELETE CASCADE,
    memory_layer TEXT NOT NULL DEFAULT 'short_term',  -- 'short_term' or 'long_term'

    -- Context
    visual_summary TEXT,      -- What the image shows relevant to this memory
    key_objects JSONB DEFAULT '[]',  -- Objects detected relevant to memory

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memory_media_memory ON memory_media_links(memory_id);
CREATE INDEX idx_memory_media_layer ON memory_media_links(memory_layer);

-- =============================================================================
-- 9. Visual Insights Table
-- =============================================================================
-- Insights derived from visual content over time

CREATE TABLE IF NOT EXISTS visual_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,

    -- Insight details
    insight_type TEXT NOT NULL,  -- 'pattern', 'preference', 'habit', 'environment', 'possession'
    insight TEXT NOT NULL,       -- The actual insight
    confidence FLOAT DEFAULT 0.5,

    -- Supporting evidence
    supporting_media JSONB DEFAULT '[]',  -- List of media_ids that support this insight
    /* Structure:
    [
        {"media_id": "...", "contribution": "Shows user's home office setup"},
        {"media_id": "...", "contribution": "Confirms preference for minimalist design"}
    ]
    */

    -- Extracted patterns
    patterns JSONB DEFAULT '{}',
    /* Structure:
    {
        "recurring_objects": ["coffee", "laptop", "plants"],
        "common_locations": ["home office", "cafe"],
        "time_patterns": {"morning": "coffee photos", "evening": "cooking"}
    }
    */

    -- Lifecycle
    first_observed_at TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at TIMESTAMPTZ DEFAULT now(),
    times_confirmed INTEGER DEFAULT 1,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_visual_insights_person ON visual_insights(person_id);
CREATE INDEX idx_visual_insights_type ON visual_insights(insight_type);
CREATE INDEX idx_visual_insights_confidence ON visual_insights(confidence DESC);

-- =============================================================================
-- 10. Helper Functions for Integration
-- =============================================================================

-- Get media for a journal entry
CREATE OR REPLACE FUNCTION get_entry_media(p_entry_id UUID)
RETURNS TABLE (
    media_id UUID,
    media_type TEXT,
    description TEXT,
    extracted_text TEXT,
    analysis JSONB,
    caption TEXT,
    relationship TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id as media_id,
        m.media_type,
        m.description,
        m.extracted_text,
        m.analysis,
        jem.caption,
        jem.relationship
    FROM media_attachments m
    JOIN journal_entry_media jem ON jem.media_id = m.id
    WHERE jem.entry_id = p_entry_id
    ORDER BY jem.created_at;
END;
$$ LANGUAGE plpgsql;

-- Search entries by visual content
CREATE OR REPLACE FUNCTION search_entries_with_media(
    p_person_id TEXT,
    p_query TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    entry_id UUID,
    entry_text TEXT,
    media_id UUID,
    media_description TEXT,
    match_source TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (je.id)
        je.id as entry_id,
        je.text as entry_text,
        m.id as media_id,
        m.description as media_description,
        CASE
            WHEN m.description ILIKE '%' || p_query || '%' THEN 'description'
            WHEN m.extracted_text ILIKE '%' || p_query || '%' THEN 'extracted_text'
            WHEN jem.caption ILIKE '%' || p_query || '%' THEN 'caption'
            ELSE 'analysis'
        END as match_source
    FROM journal_entries je
    JOIN journal_entry_media jem ON jem.entry_id = je.id
    JOIN media_attachments m ON m.id = jem.media_id
    WHERE je.person_id = p_person_id
      AND (
        m.description ILIKE '%' || p_query || '%'
        OR m.extracted_text ILIKE '%' || p_query || '%'
        OR jem.caption ILIKE '%' || p_query || '%'
        OR m.analysis::text ILIKE '%' || p_query || '%'
      )
    ORDER BY je.id, je.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Get visual context for memory recall
CREATE OR REPLACE FUNCTION get_visual_context_for_recall(
    p_person_id TEXT,
    p_query TEXT,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    media_id UUID,
    description TEXT,
    extracted_text TEXT,
    memory_type TEXT,
    subject TEXT,
    learned_facts JSONB,
    relevance TEXT
) AS $$
BEGIN
    RETURN QUERY
    -- From vision memory
    SELECT
        vm.media_id,
        m.description,
        m.extracted_text,
        vm.memory_type,
        vm.subject,
        vm.learned_facts,
        'vision_memory'::TEXT as relevance
    FROM vision_memory vm
    LEFT JOIN media_attachments m ON m.id = vm.media_id
    WHERE vm.person_id = p_person_id
      AND (
        vm.subject ILIKE '%' || p_query || '%'
        OR vm.learned_facts::text ILIKE '%' || p_query || '%'
        OR m.description ILIKE '%' || p_query || '%'
      )
    ORDER BY vm.confidence DESC, vm.times_seen DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 11. Comments
-- =============================================================================

COMMENT ON TABLE media_attachments IS 'Stores all uploaded images, screenshots, and documents';
COMMENT ON TABLE conversation_media IS 'Links media to specific conversation turns';
COMMENT ON TABLE vision_memory IS 'Long-term memory learned from visual content';
COMMENT ON TABLE parsed_documents IS 'Structured content extracted from documents';
COMMENT ON TABLE visual_context IS 'Active visual context for conversations';
COMMENT ON TABLE journal_entry_media IS 'Links media to journal entries for recall';
COMMENT ON TABLE memory_media_links IS 'Links media to memory records';
COMMENT ON TABLE visual_insights IS 'Insights derived from visual patterns';

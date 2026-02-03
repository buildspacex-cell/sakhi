-- =============================================================================
-- Phase 3: Sakhi Mesh - Unified Coordination Protocol
-- =============================================================================
-- Sakhi-to-Sakhi coordination for human interactions:
-- - Scheduling (meetings, appointments)
-- - Transactions (buying, selling)
-- - Inquiries (checking availability, getting info)
-- - Bookings (reserving services)
-- - Feedback (reviews, ratings)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- SAKHI ENTITIES
-- ─────────────────────────────────────────────────────────────────────────────
-- Who's on Sakhi - people AND businesses

CREATE TABLE IF NOT EXISTS sakhi_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id TEXT NOT NULL UNIQUE,  -- Owner of this entity

  -- Entity type
  entity_type TEXT NOT NULL DEFAULT 'personal',
    -- 'personal': Individual person
    -- 'business': Business/organization
    -- 'service': Service provider

  -- Identity
  display_name TEXT NOT NULL,
  sakhi_handle TEXT UNIQUE,  -- @username for discovery
  bio TEXT,

  -- Business-specific (NULL for personal)
  business_name TEXT,
  business_type TEXT,  -- 'retail', 'restaurant', 'service', etc.
  business_category TEXT[],  -- ['food', 'indian', 'takeout']
  location_name TEXT,
  operating_hours JSONB,
    -- {"mon": {"open": "09:00", "close": "17:00"}, ...}

  -- What this entity can do
  capabilities JSONB DEFAULT '{
    "scheduling": true,
    "transactions": false,
    "inquiries": false,
    "bookings": false
  }',

  -- Sharing preferences
  share_availability BOOLEAN DEFAULT TRUE,
  availability_detail TEXT DEFAULT 'windows',
    -- 'none', 'busy_free', 'windows', 'full'
  auto_accept_from TEXT[] DEFAULT '{}',
  require_confirmation BOOLEAN DEFAULT TRUE,
  auto_respond_inquiries BOOLEAN DEFAULT FALSE,

  -- Discovery
  discoverable BOOLEAN DEFAULT TRUE,
  verified BOOLEAN DEFAULT FALSE,

  -- Status
  active BOOLEAN DEFAULT TRUE,
  last_active_at TIMESTAMPTZ DEFAULT NOW(),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sakhi_entities_handle
  ON sakhi_entities(sakhi_handle) WHERE sakhi_handle IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sakhi_entities_type
  ON sakhi_entities(entity_type) WHERE active = TRUE AND discoverable = TRUE;
CREATE INDEX IF NOT EXISTS idx_sakhi_entities_person
  ON sakhi_entities(person_id);


-- ─────────────────────────────────────────────────────────────────────────────
-- SAKHI CONNECTIONS
-- ─────────────────────────────────────────────────────────────────────────────
-- Relationships between entities (bidirectional after acceptance)

CREATE TABLE IF NOT EXISTS sakhi_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Who's connected
  from_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),
  to_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- Connection type
  connection_type TEXT NOT NULL DEFAULT 'peer',
    -- 'peer': Equal relationship (friends)
    -- 'customer': from is customer of to
    -- 'vendor': from sells to to
    -- 'follower': one-way follow

  -- Status
  status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'connected', 'blocked', 'muted'

  -- Trust level (affects what's shared)
  trust_level TEXT DEFAULT 'standard',
    -- 'minimal': Basic info only
    -- 'standard': Normal interactions
    -- 'trusted': Can see more, auto-schedule
    -- 'vip': Priority access

  -- Permissions (what they can do)
  permissions JSONB DEFAULT '{
    "can_schedule": true,
    "can_transact": false,
    "can_auto_book": false,
    "can_see_prices": true
  }',

  -- Context
  relationship_id UUID,  -- Link to relationships table
  custom_label TEXT,  -- "My dentist", "Favorite cafe"
  notes TEXT,

  -- Interaction tracking
  first_interaction_at TIMESTAMPTZ,
  last_interaction_at TIMESTAMPTZ,
  interaction_count INT DEFAULT 0,

  connected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(from_entity_id, to_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_sakhi_connections_from
  ON sakhi_connections(from_entity_id, status);
CREATE INDEX IF NOT EXISTS idx_sakhi_connections_to
  ON sakhi_connections(to_entity_id, status);


-- ─────────────────────────────────────────────────────────────────────────────
-- COORDINATION THREADS
-- ─────────────────────────────────────────────────────────────────────────────
-- Any coordination between entities

CREATE TABLE IF NOT EXISTS coordination_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Participants
  initiator_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),
  recipient_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- What kind of coordination
  coordination_type TEXT NOT NULL,
    -- 'scheduling': Find time to meet
    -- 'inquiry': Asking a question
    -- 'transaction': Buying/selling
    -- 'booking': Reserving something
    -- 'feedback': Review/rating
    -- 'request': General ask

  -- Subject and context (type-specific)
  subject TEXT,
  context JSONB NOT NULL DEFAULT '{}',
    -- Scheduling: {event_type, duration, timeframe, location_hint}
    -- Inquiry: {question, category, urgency}
    -- Transaction: {item, quantity, price_asked}
    -- Booking: {service, date, requirements}
    -- Feedback: {rating, subject_type, subject_id}

  -- Proposed options (for scheduling/booking)
  proposed_options JSONB,
    -- [{start, end, quality, price, ...}]

  -- Status
  status TEXT NOT NULL DEFAULT 'open',
    -- 'open': Active
    -- 'pending_response': Waiting for reply
    -- 'negotiating': Back and forth
    -- 'agreed': Terms agreed
    -- 'completed': Done
    -- 'cancelled': Called off
    -- 'expired': Timed out

  -- Outcome (depends on type)
  outcome JSONB,
    -- Scheduling: {agreed_time, event_id}
    -- Transaction: {final_price, transaction_id}
    -- Booking: {confirmed_slot, booking_id}
    -- Feedback: {rating, review_id}

  -- Related records
  related_event_id UUID,
  related_transaction_id UUID,
  relationship_context JSONB,

  -- Timing
  priority TEXT DEFAULT 'normal',
  expires_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coordination_threads_initiator
  ON coordination_threads(initiator_entity_id, status);
CREATE INDEX IF NOT EXISTS idx_coordination_threads_recipient
  ON coordination_threads(recipient_entity_id, status);
CREATE INDEX IF NOT EXISTS idx_coordination_threads_type
  ON coordination_threads(coordination_type, status);
CREATE INDEX IF NOT EXISTS idx_coordination_threads_active
  ON coordination_threads(status) WHERE status IN ('open', 'pending_response', 'negotiating');


-- ─────────────────────────────────────────────────────────────────────────────
-- COORDINATION MESSAGES
-- ─────────────────────────────────────────────────────────────────────────────
-- Messages within a thread

CREATE TABLE IF NOT EXISTS coordination_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id UUID NOT NULL REFERENCES coordination_threads(id) ON DELETE CASCADE,

  -- Sender
  sender_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),
  sender_type TEXT NOT NULL DEFAULT 'sakhi',
    -- 'sakhi': Automated
    -- 'user': Direct user message
    -- 'system': System notification

  -- Message type (flexible per coordination type)
  message_type TEXT NOT NULL,
    -- Universal: 'info', 'question', 'answer', 'confirm', 'cancel'
    -- Scheduling: 'propose_times', 'accept_time', 'counter_times'
    -- Transaction: 'quote', 'offer', 'counter_offer', 'accept', 'decline'
    -- Inquiry: 'inquiry', 'response', 'followup'

  -- Content
  content JSONB NOT NULL,
    -- {
    --   "text": "Human-readable message",
    --   "data": { ... structured data ... }
    -- }

  -- Response tracking
  requires_response BOOLEAN DEFAULT FALSE,
  response_deadline TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  responded_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coordination_messages_thread
  ON coordination_messages(thread_id, created_at);


-- ─────────────────────────────────────────────────────────────────────────────
-- OFFERINGS (Products/Services)
-- ─────────────────────────────────────────────────────────────────────────────
-- What entities offer (for businesses/services)

CREATE TABLE IF NOT EXISTS sakhi_offerings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- What is it
  offering_type TEXT NOT NULL,
    -- 'product', 'service', 'experience', 'time_slot'

  name TEXT NOT NULL,
  description TEXT,
  category TEXT[],
  tags TEXT[],

  -- Pricing
  pricing JSONB,
    -- {type: "fixed"|"range"|"quote", amount, min, max, currency, unit}

  -- Availability
  available BOOLEAN DEFAULT TRUE,
  quantity_available INT,
  availability_schedule JSONB,

  -- For services
  requires_booking BOOLEAN DEFAULT FALSE,
  duration_minutes INT,
  booking_advance_hours INT,

  -- Media
  images JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sakhi_offerings_entity
  ON sakhi_offerings(entity_id) WHERE available = TRUE;


-- ─────────────────────────────────────────────────────────────────────────────
-- TRANSACTIONS
-- ─────────────────────────────────────────────────────────────────────────────
-- Completed or in-progress exchanges

CREATE TABLE IF NOT EXISTS sakhi_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Parties
  buyer_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),
  seller_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- What
  offering_id UUID REFERENCES sakhi_offerings(id),
  description TEXT NOT NULL,
  quantity INT DEFAULT 1,

  -- Money
  unit_price DECIMAL(12, 2),
  total_amount DECIMAL(12, 2),
  currency TEXT DEFAULT 'USD',

  -- Status
  status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending', 'confirmed', 'paid', 'fulfilled', 'completed', 'cancelled', 'disputed'

  -- Link to coordination
  thread_id UUID REFERENCES coordination_threads(id),

  -- Fulfillment
  fulfillment JSONB,
    -- {method, scheduled_at, completed_at, location}

  confirmed_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  fulfilled_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sakhi_transactions_buyer
  ON sakhi_transactions(buyer_entity_id, status);
CREATE INDEX IF NOT EXISTS idx_sakhi_transactions_seller
  ON sakhi_transactions(seller_entity_id, status);


-- ─────────────────────────────────────────────────────────────────────────────
-- REVIEWS
-- ─────────────────────────────────────────────────────────────────────────────
-- Feedback between entities

CREATE TABLE IF NOT EXISTS sakhi_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  reviewer_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),
  reviewed_entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- Context
  transaction_id UUID REFERENCES sakhi_transactions(id),
  offering_id UUID REFERENCES sakhi_offerings(id),
  thread_id UUID REFERENCES coordination_threads(id),

  -- Review
  rating FLOAT NOT NULL,  -- 1.0 to 5.0
  title TEXT,
  content TEXT,
  aspect_ratings JSONB,  -- {quality, communication, timeliness, value}

  -- Response
  response TEXT,
  response_at TIMESTAMPTZ,

  -- Status
  verified_interaction BOOLEAN DEFAULT FALSE,
  status TEXT DEFAULT 'published',

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sakhi_reviews_reviewed
  ON sakhi_reviews(reviewed_entity_id, status);


-- ─────────────────────────────────────────────────────────────────────────────
-- SHARED AVAILABILITY
-- ─────────────────────────────────────────────────────────────────────────────
-- Cached availability for quick coordination

CREATE TABLE IF NOT EXISTS shared_availability (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  -- What this is for
  availability_type TEXT DEFAULT 'general',
  offering_id UUID REFERENCES sakhi_offerings(id),

  -- Time range
  valid_from TIMESTAMPTZ NOT NULL,
  valid_until TIMESTAMPTZ NOT NULL,

  -- Availability at different detail levels
  busy_free JSONB NOT NULL,
    -- [{start, end, status: 'busy'|'free'}]
  windows JSONB,
    -- [{start, end, quality: 'preferred'|'available'|'suboptimal'}]
  detailed JSONB,
    -- Full availability with energy states

  computed_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(entity_id, availability_type, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_shared_availability_entity
  ON shared_availability(entity_id, valid_from, valid_until);


-- ─────────────────────────────────────────────────────────────────────────────
-- INVITE LINKS
-- ─────────────────────────────────────────────────────────────────────────────
-- Shareable connection links

CREATE TABLE IF NOT EXISTS sakhi_invite_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_id UUID NOT NULL REFERENCES sakhi_entities(id),

  code TEXT NOT NULL UNIQUE,
  custom_message TEXT,

  max_uses INT,
  uses_remaining INT,
  default_trust_level TEXT DEFAULT 'standard',

  expires_at TIMESTAMPTZ,
  active BOOLEAN DEFAULT TRUE,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sakhi_invite_links_code
  ON sakhi_invite_links(code) WHERE active = TRUE;


-- ─────────────────────────────────────────────────────────────────────────────
-- HELPER FUNCTIONS
-- ─────────────────────────────────────────────────────────────────────────────

-- Check if two entities are connected
CREATE OR REPLACE FUNCTION are_entities_connected(
  p_entity_a UUID,
  p_entity_b UUID
) RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM sakhi_connections
    WHERE status = 'connected'
      AND (
        (from_entity_id = p_entity_a AND to_entity_id = p_entity_b)
        OR (from_entity_id = p_entity_b AND to_entity_id = p_entity_a)
      )
  );
END;
$$ LANGUAGE plpgsql;


-- Get connection trust level
CREATE OR REPLACE FUNCTION get_entity_trust_level(
  p_entity_a UUID,
  p_entity_b UUID
) RETURNS TEXT AS $$
DECLARE
  trust TEXT;
BEGIN
  SELECT trust_level INTO trust
  FROM sakhi_connections
  WHERE status = 'connected'
    AND (
      (from_entity_id = p_entity_a AND to_entity_id = p_entity_b)
      OR (from_entity_id = p_entity_b AND to_entity_id = p_entity_a)
    )
  LIMIT 1;

  RETURN COALESCE(trust, 'none');
END;
$$ LANGUAGE plpgsql;


-- Get entity by person_id
CREATE OR REPLACE FUNCTION get_entity_by_person(
  p_person_id TEXT
) RETURNS UUID AS $$
DECLARE
  entity_id UUID;
BEGIN
  SELECT id INTO entity_id
  FROM sakhi_entities
  WHERE person_id = p_person_id AND active = TRUE
  LIMIT 1;

  RETURN entity_id;
END;
$$ LANGUAGE plpgsql;


-- Get shareable availability (respecting privacy)
CREATE OR REPLACE FUNCTION get_shareable_availability(
  p_entity_id UUID,
  p_requester_id UUID,
  p_start TIMESTAMPTZ,
  p_end TIMESTAMPTZ
) RETURNS JSONB AS $$
DECLARE
  trust_level TEXT;
  share_pref TEXT;
  result JSONB;
BEGIN
  trust_level := get_entity_trust_level(p_entity_id, p_requester_id);

  IF trust_level = 'none' THEN
    RETURN NULL;
  END IF;

  SELECT se.availability_detail INTO share_pref
  FROM sakhi_entities se
  WHERE se.id = p_entity_id;

  share_pref := COALESCE(share_pref, 'busy_free');

  SELECT
    CASE
      WHEN share_pref = 'none' THEN NULL
      WHEN share_pref = 'busy_free' THEN sa.busy_free
      WHEN share_pref = 'windows' AND trust_level IN ('standard', 'trusted', 'vip') THEN sa.windows
      WHEN share_pref = 'full' AND trust_level IN ('trusted', 'vip') THEN sa.detailed
      ELSE sa.busy_free
    END INTO result
  FROM shared_availability sa
  WHERE sa.entity_id = p_entity_id
    AND sa.valid_from <= p_start
    AND sa.valid_until >= p_end
  ORDER BY sa.computed_at DESC
  LIMIT 1;

  RETURN result;
END;
$$ LANGUAGE plpgsql;


-- ─────────────────────────────────────────────────────────────────────────────
-- TRIGGERS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_mesh_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sakhi_entities_updated ON sakhi_entities;
CREATE TRIGGER sakhi_entities_updated
  BEFORE UPDATE ON sakhi_entities
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

DROP TRIGGER IF EXISTS sakhi_connections_updated ON sakhi_connections;
CREATE TRIGGER sakhi_connections_updated
  BEFORE UPDATE ON sakhi_connections
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

DROP TRIGGER IF EXISTS coordination_threads_updated ON coordination_threads;
CREATE TRIGGER coordination_threads_updated
  BEFORE UPDATE ON coordination_threads
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

DROP TRIGGER IF EXISTS sakhi_offerings_updated ON sakhi_offerings;
CREATE TRIGGER sakhi_offerings_updated
  BEFORE UPDATE ON sakhi_offerings
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

DROP TRIGGER IF EXISTS sakhi_transactions_updated ON sakhi_transactions;
CREATE TRIGGER sakhi_transactions_updated
  BEFORE UPDATE ON sakhi_transactions
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();

DROP TRIGGER IF EXISTS sakhi_reviews_updated ON sakhi_reviews;
CREATE TRIGGER sakhi_reviews_updated
  BEFORE UPDATE ON sakhi_reviews
  FOR EACH ROW EXECUTE FUNCTION update_mesh_timestamp();


-- ─────────────────────────────────────────────────────────────────────────────
-- SUMMARY VIEW
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW sakhi_entity_summary AS
SELECT
  e.*,
  COALESCE(AVG(r.rating), 0) as avg_rating,
  COUNT(DISTINCT r.id) as review_count,
  COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'connected') as connection_count
FROM sakhi_entities e
LEFT JOIN sakhi_reviews r ON r.reviewed_entity_id = e.id AND r.status = 'published'
LEFT JOIN sakhi_connections c ON (c.from_entity_id = e.id OR c.to_entity_id = e.id)
WHERE e.active = TRUE
GROUP BY e.id;

export interface DoshaProfile {
  vata: number;
  pitta: number;
  kapha: number;
}

export interface ArcPhase {
  name: string;
  duration_days: number;
  emotional_state: string;
  energy_modifier: number;
  dosha_shift: DoshaProfile | null;
  themes: string[];
  events: string[];
  entry_frequency: number;
}

export interface PersonaTrait {
  name: string;
  description: string;
  intensity: number;
  journal_patterns: string[];
}

export interface LifeContext {
  occupation: string;
  relationships: Record<string, string>;
  current_challenges: string[];
  values: string[];
  hobbies: string[];
}

export interface Checkpoint {
  day: number;
  name: string;
  assertions: Record<string, any>;
}

export interface PersonaData {
  id: string;
  name: string;
  description: string;
  dosha_baseline: DoshaProfile;
  rhythm: {
    morning: string;
    afternoon: string;
    evening: string;
    best_work_time: string;
    sleep_quality: string;
  };
  traits: PersonaTrait[];
  life_context: LifeContext;
  arc: {
    name: string;
    description: string;
    phases: ArcPhase[];
  };
  writing_style: string;
  typical_entry_length: string;
  checkpoints: Checkpoint[];
}

export interface FrictionState {
  operating_system?: string;
  baseline?: { dosha_baseline: DoshaProfile };
  current_state?: {
    current_dosha: DoshaProfile;
    confidence: number;
    episode_count: number;
  };
  drift?: {
    drift_percentage: number;
    primary_contributor: string;
    direction: string;
    raw_distances: DoshaProfile;
    severity: string;
  };
  friction?: {
    state: string;
    name: string;
    description?: string;
    short: string;
    dosha: string | null;
    drift_percentage: number;
    severity: string;
    recommendations_focus?: string[];
  };
}

export interface BrainStates {
  coherence_state?: {
    coherence_score: number;
    fragmentation_index?: number;
    coherence_map?: Record<string, any>;
    summary?: string;
  };
  alignment_state?: {
    alignment_score: number;
    tension_score: number;
    conflict_zones: string[];
    action_suggestions?: string[];
    energy_profile?: string;
    focus_profile?: string;
    self_care_suggestions?: string[];
    alignment_map?: Record<string, any>;
  };
  emotion_state?: Record<string, any>;
  soul_state?: {
    longing?: any[];
    friction?: any[];
    aversions?: any[];
    conflicts?: any[];
  };
  rhythm_state?: { slots?: Record<string, string> };
  identity_momentum_state?: {
    direction: string;
    magnitude: number;
    stability: number;
    confidence: number;
    evidence_summary?: string;
    window_days?: number;
  };
  forecast_state?: Record<string, any>;
  body_state?: Record<string, any>;
  operating_system?: Record<string, any>;
}

export interface WorkerResult {
  ok: boolean;
  result?: string;
  error?: string;
}

export interface ConversationDemo {
  question: string;
  response: string;
  debug?: {
    context_used: string[];
    tone: Record<string, any>;
  };
  error?: string;
}

export interface ThemeSnapshot {
  theme: string;
  clarity_score: number;
  updated_at?: string;
}

export interface CrystallizedPattern {
  pattern_type: string;
  pattern_value: string;
  confidence: number;
  trajectory: string;
  status: string;
  mention_count: number;
  distinct_days: number;
}

export interface StateSnapshot {
  day: number;
  timestamp: string;
  personal_model: Record<string, any>;
  memory_count: number;
  pattern_count: number;
  friction_state: FrictionState;
  recent_memories: Array<{
    content: string;
    created_at: string;
  }>;
  provenance?: {
    stm_rows: number;
    embedding_rows: number;
    graph_nodes: number;
    graph_edges: number;
  };
  brain_states?: BrainStates;
  worker_results?: Record<string, WorkerResult>;
  themes?: ThemeSnapshot[];
  crystallized_patterns?: CrystallizedPattern[];
}

export interface CheckpointResult {
  passed: boolean;
  type: string;
  message: string;
}

export interface ReplayFrictionState {
  state: string;
  description?: string;
  drift_percentage: number;
  drift_direction?: string;
  primary_contributor?: string;
}

export interface TurnContinuityEvidenceDebug {
  ts?: string;
  source_ref?: string;
  snippet?: string;
  confidence?: number;
}

export interface TurnContinuityCandidateTopicDebug {
  topic_key?: string;
  topic_label?: string;
  score?: number;
  selected_count?: number;
  detail_allowed?: boolean;
}

export interface TurnContinuityCrossContextDebug {
  correlated_topic_key?: string;
  correlated_topic_label?: string;
  correlated_selected_count?: number;
  ready?: boolean;
  reason?: string;
  correlation_score?: number;
  correlation_type?: string;
  correlation_breakdown?: Record<string, number>;
  overlap_pairs?: number;
}

export interface TurnContinuityWholeStoryDebug {
  ready?: boolean;
  reason?: string;
  selected_topics?: string[];
  selected_count_total?: number;
  correlation_score?: number;
}

export interface TurnContinuityDimensionSignalDebug {
  level?: number;
  direction?: "pressured" | "neutral" | "resourced" | string;
  affected_topics?: string[];
  evidence_summary?: string;
  signal_markers?: Record<string, any>;
  surface?: boolean;
}

export interface TurnContinuityLifeDimensionsDebug {
  time_availability?: TurnContinuityDimensionSignalDebug | null;
  financial_pressure?: TurnContinuityDimensionSignalDebug | null;
  emotional_bandwidth?: TurnContinuityDimensionSignalDebug | null;
}

export interface TurnContinuityPackDebug {
  topic_key?: string;
  topic_label?: string;
  topic_confidence?: number;
  arc_compact?: {
    start_signal?: string;
    pivots_signal?: string;
    current_signal?: string;
    disclaimer?: string;
  };
  evidence?: TurnContinuityEvidenceDebug[];
  candidate_topics?: TurnContinuityCandidateTopicDebug[];
  cross_context?: TurnContinuityCrossContextDebug | null;
  whole_story?: TurnContinuityWholeStoryDebug | null;
  life_dimensions?: TurnContinuityLifeDimensionsDebug | null;
}

export interface TurnConversationEngineDebug {
  base_prompt?: string;
  prompt?: string;
  metadata?: Record<string, any>;
  recall_context?: string;
}

export interface TurnDebugData {
  continuity_pack?: TurnContinuityPackDebug;
  conversation_engine_debug?: TurnConversationEngineDebug;
  governance_decision?: Record<string, any> | null;
  governance_guard?: string;
  [key: string]: any;
}

export interface SimulationAddJournalResult {
  status?: string;
  persona_id: string;
  entry: JournalEntry;
  snapshot_day: number;
  total_days: number;
  total_entries: number;
  updated_at: string;
  turn_debug?: TurnDebugData;
}

export interface ContinuityDeepReflectionResultBody {
  reflection_mode?:
    | "deep_answer"
    | "topic_reflection"
    | "whole_story"
    | "cross_context"
    | string;
  query_context?: {
    active_query?: string;
    active_query_source?: "provided" | "topic_turn_recovery" | "derived_or_none" | "none" | string;
  };
  topic_key?: string;
  topic_label?: string;
  chat_response?: string;
  deterministic_chat_response?: string;
  chat_response_source?: "llm" | "deterministic" | string;
  llm_reflection?: {
    enabled?: boolean;
    reason?: string;
    router_source?: string;
    model?: string;
    provider?: string;
    usage?: Record<string, any>;
    input_packet?: Record<string, any>;
    prompt_messages?: Array<Record<string, any>>;
    response_text?: string;
    generated_at?: string;
    error?: string;
    [key: string]: any;
  };
  origin_story?: string;
  key_pivots?: string[];
  current_stage?: string;
  recurring_tensions?: string[];
  open_questions?: string[];
  window?: {
    from?: string;
    to?: string;
  };
  arc_summary?: Record<string, any>;
  [key: string]: any;
}

export interface ContinuityDeepReflectionResponse {
  reflection_id: string;
  topic_key?: string;
  status: string;
  mode?: "deep_answer" | "topic_reflection" | "whole_story" | "cross_context" | string;
  user_query_present?: boolean;
  error?: string | null;
  result?: ContinuityDeepReflectionResultBody;
}

export interface JournalEntry {
  day: number;
  time_of_day: string;
  content: string;
  timestamp: string;
  reply?: string;
  friction_state?: ReplayFrictionState;
}

export interface CompiledContinuityEntryTag {
  facet: string | null;
  anchor_state?: "CONFIDENT" | "UNCERTAIN" | "UNKNOWN";
  facet_state?: "CONFIDENT" | "UNCERTAIN" | "UNKNOWN";
  decision_state: string | null;
  stance: string | null;
  scalar: number | null;
  confidence: number;
  matched_terms?: string[];
  trace?: Record<string, any>;
}

export interface CompiledContinuityEventRef {
  day: number;
  ts: string;
  time_of_day: string;
  facet: string | null;
  anchor_state?: "CONFIDENT" | "UNCERTAIN" | "UNKNOWN";
  facet_state?: "CONFIDENT" | "UNCERTAIN" | "UNKNOWN";
  decision_state: string | null;
  stance: string | null;
  scalar: number | null;
  excerpt: string;
}

export interface CompiledContinuityArc {
  id: string;
  key: string;
  start_ts: string;
  end_ts: string;
  span_days: number;
  element_count: number;
  phase_count: number;
  phases: Array<{
    index: number;
    start_ts: string;
    end_ts: string;
    start_day: number;
    end_day: number;
    element_count: number;
    stats: Record<string, any>;
  }>;
  features: {
    direction: string;
    stability: number;
    oscillation: number;
    momentum: number | null;
    average_rate: number | null;
    density: number | null;
    change_points: number[];
  } | null;
  event_refs: CompiledContinuityEventRef[];
}

export interface CompiledContinuityTopic {
  anchor: string;
  label: string;
  confidence: number;
  selected_count: number;
  entry_days: number[];
  entry_tags: Record<string, CompiledContinuityEntryTag>;
  surface?: {
    mirror_allowed: boolean;
    detail_allowed: boolean;
    classification_score: number;
    coherence_score: number;
    blocked_reason: string | null;
  };
  arc: CompiledContinuityArc;
}

export interface SimulationContinuityData {
  version: number;
  taxonomy_version?: string;
  compiler_version?: string;
  threshold_profile_version?: string;
  compiled_at?: string;
  inputs_hash?: string;
  generated_at: string;
  topics: CompiledContinuityTopic[];
}

export interface SimulationData {
  persona_id: string;
  persona: PersonaData;
  user_id: string;
  start_time: string;
  end_time: string | null;
  total_days: number;
  total_entries: number;
  all_checkpoints_passed: boolean;
  snapshots: StateSnapshot[];
  checkpoint_results: Record<string, CheckpointResult[]>;
  entries: JournalEntry[];
  errors: any[];
  // Real pipeline metadata (set by export_real_simulation.py)
  real_pipeline?: boolean;
  generated_at?: string;
  // Conversation demo Q&A pairs (v2 — full brain)
  conversation_demo?: ConversationDemo[];
  // Governance evaluation result
  governance_result?: {
    action: string;
    reasons: string[];
    triggers: string[];
    is_blocked: boolean;
    is_allowed: boolean;
    requires_confirmation: boolean;
    violations: Array<{
      constraint_id: string;
      field: string;
      operator: string;
      expected: number | string;
      description: string;
      actual: number | string | null;
      message: string;
    }>;
  };
  continuity?: SimulationContinuityData;
}

// Phase boundary for timeline visualization
export interface PhaseBoundary {
  start: number;
  end: number;
  phase: ArcPhase;
}

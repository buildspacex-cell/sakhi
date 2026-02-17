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

export interface JournalEntry {
  day: number;
  time_of_day: string;
  content: string;
  timestamp: string;
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
}

// Phase boundary for timeline visualization
export interface PhaseBoundary {
  start: number;
  end: number;
  phase: ArcPhase;
}

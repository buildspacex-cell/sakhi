// Governance decision from real Kala GovernanceGate API
export interface GateDecision {
  status: string;
  scenario_id: string;
  profile: string;
  action: "allow" | "require_confirmation" | "block" | "require_reconciliation";
  reasons: string[];
  triggers: string[];
  is_blocked: boolean;
  is_allowed: boolean;
  requires_confirmation: boolean;
  violations: Violation[];
}

export interface Violation {
  constraint_id: string;
  field: string;
  operator: string;
  expected: number | string;
  description: string;
  actual: number | string | null;
  message: string;
}

export interface LedgerEvent {
  id: string;
  timestamp: string;
  person_id: string;
  event_type: "proposed" | "committed" | "validated" | "rejected" | "reconciled";
  action: string;
  actor: string;
  data: Record<string, unknown>;
  reason: string;
}

export interface ConstraintInfo {
  id: string;
  type: string;
  field: string;
  operator: string;
  value: number | string;
  description: string;
  priority: number;
}

export interface SimulationState {
  operating_system: Record<string, unknown>;
  constraint_count: number;
  constraints: ConstraintInfo[];
  person_id: string;
}

// Profile configuration
export interface ProfileConfig {
  id: string;
  label: string;
  osType: string;
  dosha: string;
  color: string;
  colorDim: string;
  doshaScores: { vata: number; pitta: number; kapha: number };
}

// Scenario configuration
export interface ScenarioConfig {
  id: string;
  time: string;
  title: string;
  subtitle: string;
  icon: string;
  // Per-profile data
  profiles: Record<string, ProfileScenarioData>;
}

export interface ProfileScenarioData {
  // Action context sent to real Kala API
  actionContext: {
    proposed_action: string;
    proposed_hour: number;
    drift_percentage: number;
    friction_state: string;
    user_text: string;
  };
  // Static display data (secondary to governance objects)
  driftPercentage: number;
  driftTrend?: { delta: number; days: number };
  frictionState: string;
  conversationText: string;
  intelligenceItems: IntelligenceItem[];
}

export interface IntelligenceItem {
  label: string;
  value: string;
  source: string;
}

// Intelligence data from real backend (objectives, events, drift trend)
export interface IntelligenceData {
  objectives: ObjectiveVersion[];
  commitment_events: CommitmentEvent[];
  drift_trend: DriftTrend | null;
  constraints: IntelligenceConstraint[];
  intelligence_items: IntelligenceItem[];
}

export interface ObjectiveVersion {
  objective_id: string;
  version: number;
  title: string;
  description: string;
  source: string;
  reason: string;
  created_at: string | null;
  parent_version: number | null;
}

export interface CommitmentEvent {
  id: string;
  action: string;
  context: string;
  drift_at_time: number | null;
  days_ago: number | null;
  timestamp: string | null;
}

export interface DriftTrend {
  values: number[];
  delta: number;
  days: number;
  direction: "rising" | "falling" | "stable";
}

export interface IntelligenceConstraint {
  id: string;
  description: string;
  priority: number;
  source: string;
}

// ---------------------------------------------------------------------------
// Replay types (30-day conversation replay)
// ---------------------------------------------------------------------------

export interface ReplayFrictionState {
  state: string;
  description?: string;
  drift_percentage: number;
  drift_direction?: string;
  primary_contributor?: string;
}

export interface ReplayEntry {
  day: number;
  time_of_day: string;
  content: string;
  timestamp: string;
  reply?: string;
  friction_state?: ReplayFrictionState;
}

export interface GovernanceResult {
  action: string;
  reasons: string[];
  triggers: string[];
  is_blocked: boolean;
  is_allowed: boolean;
  requires_confirmation: boolean;
  violations: Violation[];
}

export interface ArcPhase {
  name: string;
  duration_days: number;
  emotional_state: string;
  themes?: string[];
  energy_modifier?: number;
  events?: string[];
  entry_frequency?: number;
}

export interface ReplayPersona {
  id: string;
  name: string;
  description: string;
  dosha_baseline: { vata: number; pitta: number; kapha: number };
  arc: { name: string; description: string; phases: ArcPhase[] };
  governance_scenario?: {
    user_text: string;
    proposed_action: string;
    proposed_hour: number;
  };
}

export interface ReplayData {
  persona_id: string;
  user_id: string;
  persona: ReplayPersona;
  total_days: number;
  total_entries: number;
  entries: ReplayEntry[];
  snapshots: Array<{
    day: number;
    friction_state?: {
      drift?: { drift_percentage: number; primary_contributor: string; direction: string; severity: string };
      friction?: { state: string; name: string; description: string; drift_percentage: number; severity: string; recommendations_focus?: string[] };
    };
    pattern_count?: number;
    memory_count?: number;
    crystallized_patterns?: unknown[];
  }>;
  governance_result?: GovernanceResult;
}

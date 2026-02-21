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
  id: "adaptive" | "performance" | "conservation";
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
  frictionState: string;
  conversationText: string;
  intelligenceItems: IntelligenceItem[];
}

export interface IntelligenceItem {
  label: string;
  value: string;
  source: string;
}

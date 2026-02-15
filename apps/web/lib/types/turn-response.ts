/**
 * TurnResponseProduct — canonical response contract for POST /v2/turn.
 *
 * Only these fields are guaranteed at the top level in production.
 * Debug fields are nested under `debug_data` when SAKHI_DEBUG_RESPONSE=1 or ?debug=1.
 */
export interface TurnResponseProduct {
  reply: string;
  sessionId?: string;
  tone?: string;
  toneBlueprint?: Record<string, unknown>;
  tone_blueprint?: Record<string, unknown>;
  entry_id?: string;
  friction_state?: Record<string, unknown>;
  personalized_recommendations?: Record<string, unknown>;
  adaptive_response?: {
    strategy?: {
      mode?: string;
      reasoning?: string;
      why?: string;
    };
    context?: {
      friction_state?: string;
      drift_percentage?: number;
    };
    pipeline_stages?: Record<string, boolean>;
    errors?: Record<string, string>;
    warnings?: string[];
  };
  journaling_ai?: Record<string, unknown>;
  memory_recall?: Array<{
    text?: string;
    content?: string;
    type?: string;
    score?: number;
  }>;
  agent_task_context?: AgentTaskContext;

  /** Only present when debug is enabled. */
  debug_data?: Record<string, unknown>;
}

export interface AgentTaskContext {
  new_task?: {
    formatted_plan: string;
    [key: string]: unknown;
  };
  execution?: {
    status: string;
    message: string;
    [key: string]: unknown;
  };
  rejected?: boolean;
  confirmed?: boolean;
  message?: string;
  pending_task?: Record<string, unknown>;
  awaiting_confirmation?: boolean;
}

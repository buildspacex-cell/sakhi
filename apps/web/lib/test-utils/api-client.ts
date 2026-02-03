/**
 * API Test Client for Sakhi
 *
 * Provides typed API client for testing and development.
 * Use this instead of raw fetch calls for better type safety and error handling.
 *
 * Usage:
 *   import { apiClient, DEMO_USER_ID } from '@/lib/test-utils/api-client';
 *
 *   // Send a conversation turn
 *   const response = await apiClient.turn.send({
 *     personId: DEMO_USER_ID,
 *     message: "Hello!",
 *   });
 *
 *   // Get friction state
 *   const state = await apiClient.friction.getCurrentState(DEMO_USER_ID);
 */

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

/** Demo user ID - has seeded data for testing */
export const DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90";

/** API base URL - uses environment or defaults to localhost */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface TurnRequest {
  personId: string;
  message: string;
  threadId?: string;
}

export interface TurnResponse {
  reply: string;
  thread_id: string;
  turn_id: string;
  signals?: Record<string, unknown>;
}

export interface FrictionState {
  operating_system: {
    type: "adaptive" | "performance" | "conservation";
    primary_dosha: "vata" | "pitta" | "kapha";
  };
  current_mode: "clarity" | "activation" | "recovery";
  friction_state: "chaos" | "intensity" | "stagnation" | null;
  energy_level: number;
  updated_at: string;
}

export interface MemoryRecallRequest {
  personId: string;
  query: string;
  limit?: number;
}

export interface MemoryItem {
  id: string;
  content: string;
  source: string;
  similarity: number;
  created_at: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Base Client
// ─────────────────────────────────────────────────────────────────────────────

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error: ApiError = {
      detail: await response.text(),
      status: response.status,
    };
    throw error;
  }

  return response.json();
}

// ─────────────────────────────────────────────────────────────────────────────
// API Client
// ─────────────────────────────────────────────────────────────────────────────

export const apiClient = {
  /**
   * Conversation turn endpoints
   */
  turn: {
    /**
     * Send a conversation turn and get Sakhi's response
     */
    async send(req: TurnRequest): Promise<TurnResponse> {
      return request<TurnResponse>("/v2/turn", {
        method: "POST",
        body: JSON.stringify({
          person_id: req.personId,
          message: req.message,
          thread_id: req.threadId,
        }),
      });
    },

    /**
     * Get conversation history for a thread
     */
    async getHistory(
      personId: string,
      threadId: string
    ): Promise<{ turns: TurnResponse[] }> {
      return request(`/v2/conversation/history?person_id=${personId}&thread_id=${threadId}`);
    },
  },

  /**
   * Friction Framework endpoints
   */
  friction: {
    /**
     * Get current friction state for a user
     */
    async getCurrentState(personId: string): Promise<FrictionState> {
      return request(`/friction-framework/state/current?person_id=${personId}`);
    },

    /**
     * Get recommendations based on current state
     */
    async getRecommendations(
      personId: string
    ): Promise<{ recommendations: Array<{ type: string; content: string }> }> {
      return request(`/friction/recommendations?person_id=${personId}`);
    },
  },

  /**
   * Memory endpoints
   */
  memory: {
    /**
     * Recall memories matching a query
     */
    async recall(req: MemoryRecallRequest): Promise<{ memories: MemoryItem[] }> {
      return request<{ memories: MemoryItem[] }>("/memory/recall", {
        method: "POST",
        body: JSON.stringify({
          person_id: req.personId,
          query: req.query,
          limit: req.limit || 10,
        }),
      });
    },

    /**
     * Get recent memories for a user
     */
    async getRecent(
      personId: string,
      limit: number = 10
    ): Promise<{ memories: MemoryItem[] }> {
      return request(`/memory/recent?person_id=${personId}&limit=${limit}`);
    },
  },

  /**
   * Health check endpoints
   */
  health: {
    /**
     * Check if API is running
     */
    async check(): Promise<{ status: string }> {
      return request("/health");
    },

    /**
     * Get detailed health status
     */
    async detailed(): Promise<{
      status: string;
      database: boolean;
      redis: boolean;
      workers: number;
    }> {
      return request("/health/detailed");
    },
  },

  /**
   * Lab/debug endpoints (dev only)
   */
  lab: {
    /**
     * Get all memory details for debugging
     */
    async getMemoryDetails(
      personId: string
    ): Promise<Record<string, unknown>> {
      return request(`/lab/memory-details?person_id=${personId}`);
    },

    /**
     * Run a specific worker manually
     */
    async runWorker(
      workerName: string,
      personId: string,
      turnId: string
    ): Promise<{ success: boolean; result: unknown }> {
      return request("/lab/run-worker", {
        method: "POST",
        body: JSON.stringify({
          worker_name: workerName,
          person_id: personId,
          turn_id: turnId,
        }),
      });
    },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Test Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Wait for API to be ready (useful in tests)
 */
export async function waitForApi(
  maxWaitMs: number = 10000,
  intervalMs: number = 500
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    try {
      await apiClient.health.check();
      return true;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
  }

  return false;
}

/**
 * Send multiple turns in sequence (for testing conversations)
 */
export async function sendConversation(
  personId: string,
  messages: string[]
): Promise<TurnResponse[]> {
  const responses: TurnResponse[] = [];
  let threadId: string | undefined;

  for (const message of messages) {
    const response = await apiClient.turn.send({
      personId,
      message,
      threadId,
    });
    threadId = response.thread_id;
    responses.push(response);
  }

  return responses;
}

/**
 * Create a test conversation and return thread ID
 */
export async function createTestConversation(
  personId: string = DEMO_USER_ID
): Promise<string> {
  const response = await apiClient.turn.send({
    personId,
    message: "Test conversation start",
  });
  return response.thread_id;
}

import { useState, useCallback } from "react";
import { config } from "../lib/config";
import { supabase } from "../lib/supabase";

// =============================================================================
// TYPES
// =============================================================================

export interface DoshaBaseline {
  vata: number;
  pitta: number;
  kapha: number;
}

export interface OSDetails {
  description: string;
  strengths: string[];
  patterns_to_watch: string[];
}

export interface OnboardingResponse {
  success: boolean;
  person_id: string;
  phase_completed: string;
  phases_remaining: string[];
  operating_system: string;
  primary: string;
  secondary: string | null;
  dosha_baseline: DoshaBaseline;
  os_confidence: number;
  os_label: string;
  os_details: OSDetails;
}

export type OnboardingPhase = "phase1" | "phase2a" | "phase2b";

// =============================================================================
// HOOK
// =============================================================================

export function useOnboarding() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [osResult, setOsResult] = useState<OnboardingResponse | null>(null);

  const submitOnboarding = useCallback(
    async (
      phase: OnboardingPhase,
      responses: Record<string, string | string[]>
    ): Promise<OnboardingResponse | null> => {
      setLoading(true);
      setError(null);

      try {
        // Get current user ID from Supabase auth
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user?.id) {
          throw new Error("User not authenticated");
        }

        const payload = {
          person_id: user.id,
          source: "mobile",
          phase,
          responses,
          completed_at: new Date().toISOString(),
        };

        const response = await fetch(`${config.backendUrl}/onboarding/submit`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data: OnboardingResponse = await response.json();
        setOsResult(data);
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setError(message);
        console.error("Onboarding submission failed:", err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    loading,
    error,
    osResult,
    submitOnboarding,
    clearError,
  };
}

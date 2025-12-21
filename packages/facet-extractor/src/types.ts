import type { Facet, Message } from "@sakhi/contracts";

export type FacetExtractorInput = {
  message: Message;
  transcript?: {
    raw: string;
    asr_confidence?: number;
  };
  metadata?: Record<string, unknown>;
};

export type FacetExtractorOutput = {
  facets: Facet[];
  diagnostics?: {
    tokens_used?: number;
    latency_ms?: number;
    error?: string;
    decision_intent?: string;
  };
};

export interface FacetExtractor {
  extract(input: FacetExtractorInput): Promise<FacetExtractorOutput>;
}

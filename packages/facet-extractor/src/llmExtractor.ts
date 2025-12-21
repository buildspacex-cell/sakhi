import { FacetSchema } from "@sakhi/contracts";
import type { FacetExtractor, FacetExtractorInput, FacetExtractorOutput } from "./types";

export type LLMFacetExtractorConfig = {
  apiKey: string;
  model?: string;
  baseUrl?: string;
};

type LLMFacet = {
  type: "person" | "activity";
  confidence: number;
  dimensions: Record<string, any>;
  extras?: Record<string, any>;
  span?: { start: number; end: number };
};

export class LLMFacetExtractor implements FacetExtractor {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly baseUrl: string;

  constructor({ apiKey, model = "deepseek/deepseek-chat", baseUrl = "https://openrouter.ai/api/v1/chat/completions" }: LLMFacetExtractorConfig) {
    this.apiKey = apiKey;
    this.model = model;
    this.baseUrl = baseUrl;
  }

  async extract(input: FacetExtractorInput): Promise<FacetExtractorOutput> {
    const prompt = this.buildPrompt(input);
    const response = await fetch(this.baseUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: "system", content: "You extract structured facets (person & activity) from user messages." },
          { role: "user", content: prompt }
        ],
        response_format: { type: "json_schema", json_schema: this.schema() }
      })
    });
    if (!response.ok) {
      throw new Error(`Facet extractor LLM failed: ${response.status} ${await response.text()}`);
    }
    const data = await response.json();
    const content = data.choices?.[0]?.message?.content;
    const parsed = content ? JSON.parse(content) : { facets: [] };
    const facets = (parsed.facets as LLMFacet[]).map((facet, idx) =>
      FacetSchema.parse({
        schema_version: "0.1.0",
        id: `${input.message.id}-llm-${idx}`,
        message_id: input.message.id,
        type: facet.type,
        confidence: facet.confidence,
        dimensions: facet.dimensions,
        span: facet.span,
        extras: facet.extras
      })
    );
    return {
      facets,
      diagnostics: {
        latency_ms: data.usage?.response_time_ms,
        tokens_used: data.usage?.total_tokens
      }
    };
  }

  private buildPrompt(input: FacetExtractorInput): string {
    return `Message: """${input.message.content.text}"""\nReturn JSON with facets, each including type (person/activity), confidence (0-1), dimensions (need/intention etc.), and any extras (decision intents).`;
  }

  private schema() {
    return {
      name: "facet_response",
      schema: {
        type: "object",
        properties: {
          facets: {
            type: "array",
            items: {
              type: "object",
              properties: {
                type: { type: "string", enum: ["person", "activity"] },
                confidence: { type: "number" },
                dimensions: { type: "object" },
                extras: { type: "object" },
                span: {
                  type: "object",
                  properties: {
                    start: { type: "number" },
                    end: { type: "number" }
                  }
                }
              },
              required: ["type", "confidence", "dimensions"]
            }
          }
        },
        required: ["facets"]
      }
    };
  }
}

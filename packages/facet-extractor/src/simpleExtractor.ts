import { FacetSchema } from "@sakhi/contracts";
import type { FacetExtractor, FacetExtractorInput, FacetExtractorOutput } from "./types";

const NEED_KEYWORDS: Record<string, "listen" | "plan" | "encourage" | "clarify" | "vent"> = {
  overwhelmed: "listen",
  exhausted: "listen",
  tired: "listen",
  "help me": "plan",
  "need to plan": "plan",
  "can you remind": "plan",
  "cheer me": "encourage",
  "hold me accountable": "encourage",
  "question": "clarify",
  "can you clarify": "clarify",
  "vent": "vent"
};

const ACTIVITY_VERBS = ["finish", "email", "book", "call", "schedule", "write", "review", "prep", "plan"];
const DECISION_PATTERNS: Array<{ intent: "wardrobe" | "preworkout-meal" | "travel-pack" | "route" | "gift"; regex: RegExp; slots?: (text: string) => Record<string, string> }> = [
  {
    intent: "wardrobe",
    regex: /(what\s+should\s+i\s+wear|outfit|dress\s+code)/i,
    slots: (text) => ({
      setting: /wedding|party/i.test(text) ? "event" : /conference|meeting/i.test(text) ? "conference" : undefined,
      indoor: /outdoor|lawn/i.test(text) ? "outdoor" : undefined,
      climate: /humid|hot/i.test(text) ? "humid" : undefined
    })
  },
  {
    intent: "preworkout-meal",
    regex: /(eat|snack).*(before|pre).*workout/i,
    slots: (text) => ({
      window: /\b(\d{2})\s?m/i.test(text) ? `${RegExp.$1}m` : undefined,
      intensity: /yoga|vinyasa/i.test(text) ? "vinyasa" : undefined
    })
  },
  {
    intent: "travel-pack",
    regex: /(pack|packing)\s+(list|for)/i,
    slots: (text) => ({
      climate: /cold|snow/i.test(text) ? "cold" : /hot|humid/i.test(text) ? "hot" : undefined,
      duration: (text.match(/(\d+)\s*(day|night)/i)?.[1]) ?? undefined
    })
  },
  {
    intent: "route",
    regex: /(best\s+way|route|how\s+do\s+i\s+get)/i,
    slots: (text) => ({
      arrival: text.match(/by\s+(\d{1,2}:?\d{0,2}\s*(?:am|pm)?)/i)?.[1]
    })
  },
  {
    intent: "gift",
    regex: /(gift|present)/i,
    slots: (text) => ({
      occasion: /birthday|anniversary|wedding/i.exec(text)?.[0],
      recipient: /friend|partner|mom|dad|boss/i.exec(text)?.[0]
    })
  }
];

export class SimpleFacetExtractor implements FacetExtractor {
  async extract(input: FacetExtractorInput): Promise<FacetExtractorOutput> {
    const text = input.message.content.text.toLowerCase();
    const facets = [
      ...this.extractPersonFacet(input.message.id, text),
      ...this.extractActivityFacets(input.message.id, text),
      ...this.extractDecisionFacets(input.message.id, text)
    ].map((facet) => FacetSchema.parse(facet));

    return {
      facets,
      diagnostics: {
        latency_ms: 0
      }
    };
  }

  private extractPersonFacet(messageId: string, text: string) {
    const matches = Object.entries(NEED_KEYWORDS).filter(([keyword]) => text.includes(keyword));
    if (matches.length === 0) return [];

    return [
      {
        schema_version: "0.1.0",
        id: `${messageId}-person`,
        message_id: messageId,
        type: "person" as const,
        confidence: 0.6,
        dimensions: {
          need: matches[0][1],
          intention: matches[0][1] === "plan" ? "plan" : "vent"
        }
      }
    ];
  }

  private extractActivityFacets(messageId: string, text: string) {
    const sentences = text.split(/[.?!]/).map((s) => s.trim());
    const facets = [];
    for (const sentence of sentences) {
      const verb = ACTIVITY_VERBS.find((v) => sentence.startsWith(v) || sentence.includes(` ${v} `));
      if (!verb) continue;
      facets.push({
        schema_version: "0.1.0",
        id: `${messageId}-activity-${facets.length + 1}`,
        message_id: messageId,
        type: "activity" as const,
        confidence: 0.5,
        dimensions: {
          action: sentence,
          effort: sentence.includes("deck") || sentence.includes("review") ? "deep" : "light",
          importance: sentence.includes("tomorrow") ? "high" : "medium",
          horizon: sentence.includes("today") ? "today" : sentence.includes("tomorrow") ? "soon" : "later"
        }
      });
    }
    return facets;
  }

  private extractDecisionFacets(messageId: string, text: string) {
    const matches = DECISION_PATTERNS.filter(({ regex }) => regex.test(text));
    return matches.map((match, idx) => ({
      schema_version: "0.1.0",
      id: `${messageId}-decision-${idx + 1}`,
      message_id: messageId,
      type: "activity" as const,
      confidence: 0.7,
      dimensions: {
        action: `decision:${match.intent}`,
        effort: "light",
        importance: "medium"
      },
      extras: {
        decision_intent: match.intent,
        decision_slots: match.slots ? match.slots(text) : {}
      }
    }));
  }
}

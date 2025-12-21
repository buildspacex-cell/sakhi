import { PlanGraphSchema, type Facet } from "@sakhi/contracts";
import type { PlannerInput } from "./types";
import { DecisionEngine, DecisionResult } from "@sakhi/decision-engine";

export type PlannerPattern = {
  name: string;
  predicate: (input: PlannerInput) => boolean;
  build: (input: PlannerInput) => PlanGraphSchema["_input"];
};

const reflectionOnlyPattern: PlannerPattern = {
  name: "reflect-only",
  predicate: ({ facets }) =>
    facets.some((f) => f.type === "person" && f.dimensions.need === "listen") &&
    !facets.some((f) => f.type === "activity"),
  build: ({ context }) => ({
    schema_version: "0.1.0",
    objective_now: "listen",
    learning_goal: {
      hypothesis: "stressor_overload?"
    },
    steps: [
      {
        type: "reflection",
        text_template: "It sounds like things feel heavy right now. I'm here with you."
      }
    ]
  })
};

const reflectPlusQuestionPattern: PlannerPattern = {
  name: "reflect-plus-question",
  predicate: ({ facets }) =>
    facets.some((f) => f.type === "person" && f.dimensions.need === "clarify"),
  build: () => ({
    schema_version: "0.1.0",
    objective_now: "clarify",
    learning_goal: {
      micro_question: "What would reduce the pressure right now?"
    },
    steps: [
      {
        type: "reflection",
        text_template: "Noted the mix of feelings."
      },
      {
        type: "question",
        target: "person",
        purpose: "clarify",
        template: "What would help most in the next hour?"
      }
    ]
  })
};

const planLitePattern: PlannerPattern = {
  name: "plan-lite",
  predicate: ({ facets }) =>
    facets.some((f) => f.type === "activity" && f.dimensions.effort === "light"),
  build: ({ facets }) => {
    const activity = facets.find((f) => f.type === "activity" && f.dimensions.effort === "light");
    return {
      schema_version: "0.1.0",
      objective_now: "plan",
      learning_goal: {
        hypothesis: activity?.dimensions.action ? `prefers_${activity.dimensions.action}` : undefined
      },
      steps: [
        {
          type: "reflection",
          text_template: "Captured what you need."
        },
        {
          type: "action.create",
          payload: {
            title: activity?.dimensions.action ?? "Follow up",
            notes: "Created from plan-lite pattern"
          }
        }
      ]
    };
  }
};

const planDeepPattern: PlannerPattern = {
  name: "plan-deep",
  predicate: ({ facets }) =>
    facets.some((f) => f.type === "activity" && f.dimensions.effort === "deep"),
  build: ({ facets, context }) => {
    const activity = facets.find((f) => f.type === "activity" && f.dimensions.effort === "deep");
    const highEnergyBlock = context.schedule_window.free_blocks.find((b) => b.energy === "high");
    return {
      schema_version: "0.1.0",
      objective_now: "plan",
      learning_goal: {
        micro_question: "Would a focused block help?"
      },
      steps: [
        {
          type: "reflection",
          text_template: "That work deserves a proper runway."
        },
        {
          type: "calendar.block.propose",
          payload: {
            title: activity?.dimensions.action ?? "Focus block",
            start: highEnergyBlock?.start,
            duration_minutes: activity?.dimensions.duration_minutes ?? 60
          }
        }
      ]
    };
  }
};

const encouragePattern: PlannerPattern = {
  name: "encourage-track",
  predicate: ({ facets }) =>
    facets.some((f) => f.type === "person" && f.dimensions.need === "encourage"),
  build: () => ({
    schema_version: "0.1.0",
    objective_now: "encourage",
    learning_goal: {
      hypothesis: "habit_support?"
    },
    steps: [
      {
        type: "reflection",
        text_template: "Progress counts, even if small."
      },
      {
        type: "nudge.schedule",
        payload: {
          title: "Gentle check-in",
          send_at: new Date(Date.now() + 60 * 60 * 1000).toISOString()
        }
      }
    ]
  })
};

const decisionPattern = (engine: DecisionEngine): PlannerPattern => ({
  name: "decision-template",
  predicate: ({ facets }) => facets.some((f) => Boolean((f as any).extras?.decision_intent)),
  build: ({ facets }) => {
    const target = facets.find((f) => (f as any).extras?.decision_intent);
    const extras = (target as any)?.extras ?? {};
    const intent = extras.decision_intent as DecisionResult["intent"];
    const slots = (extras.decision_slots ?? {}) as Record<string, string>;
    const result = engine.decide(intent, slots);
    const optionsText = result.options.map((opt, idx) => `${idx + 1}. ${opt.label} – ${opt.rationale}`).join(" ");
    return {
      schema_version: "0.1.0",
      objective_now: "clarify",
      learning_goal: { micro_question: result.microQuestion, hypothesis: result.learningHints?.[0]?.key },
      extras: { learningHints: result.learningHints },
      steps: [
        {
          type: "reflection",
          text_template: `Here are ${result.intent} ideas: ${optionsText}`
        },
        {
          type: "question",
          target: "person",
          purpose: "confirm",
          template: result.microQuestion ?? "Which option feels best?"
        }
      ]
    };
  }
});

export const createPatterns = (engine: DecisionEngine): PlannerPattern[] => [
  decisionPattern(engine),
  reflectionOnlyPattern,
  reflectPlusQuestionPattern,
  planLitePattern,
  planDeepPattern,
  encouragePattern
];

export function pickPattern(patterns: PlannerPattern[], input: PlannerInput): PlannerPattern {
  return patterns.find((pattern) => pattern.predicate(input)) ?? reflectionOnlyPattern;
}

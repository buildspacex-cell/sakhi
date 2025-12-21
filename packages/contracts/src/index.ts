import { z } from "zod";

export const SCHEMA_VERSION = "0.1.0" as const;

/**
 * Shared enums
 */
export const ModalityEnum = z.enum(["text", "voice", "sensor", "system"]);
export const ChannelEnum = z.enum([
  "mobile",
  "web",
  "calendar",
  "wearable",
  "integration",
  "system"
]);
export const PersonNeedEnum = z.enum(["listen", "plan", "encourage", "clarify", "vent", "unknown"]);
export const PersonIntentionEnum = z.enum(["vent", "plan", "decide", "reflect", "report", "unknown"]);
export const ActivityEffortEnum = z.enum(["light", "medium", "deep"]);
export const ActivityImportanceEnum = z.enum(["low", "medium", "high", "critical"]);
export const ObjectiveEnum = z.enum(["listen", "reflect", "clarify", "plan", "encourage"]);

const SchemaVersionField = z.string().default(SCHEMA_VERSION);

const GeoTagSchema = z.object({
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  accuracy_m: z.number().positive().optional()
});

const SpanSchema = z.object({
  start: z.number().int().nonnegative(),
  end: z.number().int().nonnegative()
});

/**
 * Message contract
 */
export const MessageSchema = z.object({
  schema_version: SchemaVersionField,
  id: z.string(),
  user_id: z.string(),
  timestamp: z.string(),
  content: z.object({
    text: z.string(),
    modality: ModalityEnum,
    locale: z.string().default("en-US")
  }),
  source: z.object({
    channel: ChannelEnum,
    device: z.string().optional()
  }),
  metadata: z
    .object({
      timezone: z.string(),
      geotag: GeoTagSchema.optional(),
      extras: z.record(z.unknown()).optional()
    })
    .default({})
});

/**
 * Facet contracts
 */
const FacetBaseSchema = z.object({
  schema_version: SchemaVersionField,
  id: z.string().optional(),
  message_id: z.string(),
  confidence: z.number().min(0).max(1),
  span: SpanSchema.optional(),
  extras: z.record(z.unknown()).optional()
});

export const PersonFacetSchema = FacetBaseSchema.extend({
  type: z.literal("person"),
  dimensions: z
    .object({
      valence: z.number().min(-1).max(1).optional(),
      arousal: z.number().min(0).max(1).optional(),
      need: PersonNeedEnum.optional(),
      intention: PersonIntentionEnum.optional(),
      emotion: z.string().optional(),
      energy: z.enum(["low", "neutral", "high"]).optional()
    })
    .default({})
});

export const ActivityFacetSchema = FacetBaseSchema.extend({
  type: z.literal("activity"),
  dimensions: z
    .object({
      action: z.string().optional(),
      horizon: z.enum(["now", "today", "soon", "later"]).optional(),
      effort: ActivityEffortEnum.optional(),
      importance: ActivityImportanceEnum.optional(),
      duration_minutes: z.number().int().positive().optional(),
      context: z.string().optional()
    })
    .default({})
});

export const FacetSchema = z.discriminatedUnion("type", [PersonFacetSchema, ActivityFacetSchema]);

/**
 * Context pack
 */
export const RecentItemSchema = z.object({
  id: z.string(),
  message_id: z.string().optional(),
  text: z.string(),
  timestamp: z.string(),
  facets: z.array(FacetSchema).optional(),
  delta: z.record(z.unknown()).optional()
});

export const EpisodicRefSchema = z.object({
  id: z.string(),
  when: z.string(),
  summary: z.string(),
  relevance: z.number().min(0).max(1).optional(),
  link: z.string().optional()
});

export const SemanticProfileSchema = z.object({
  traits: z.record(z.unknown()).default({}),
  preferences: z.record(z.unknown()).default({}),
  values: z.array(z.string()).default([])
});

export const ScheduleEventSchema = z.object({
  id: z.string(),
  title: z.string(),
  start: z.string(),
  end: z.string(),
  location: z.string().optional(),
  category: z.enum(["focus", "personal", "meeting", "health", "other"]).optional()
});

export const FreeBlockSchema = z.object({
  start: z.string(),
  end: z.string(),
  energy: z.enum(["low", "medium", "high"]).optional()
});

export const ContextPackSchema = z.object({
  schema_version: SchemaVersionField,
  user_id: z.string(),
  turn_id: z.string(),
  now: z.object({
    clock: z.string(),
    weekday: z.string(),
    season: z.string().optional()
  }),
  rhythms: z
    .object({
      circadian_phase: z.string().optional(),
      breath_rate: z.number().optional(),
      awareness_coherence: z.number().min(0).max(1).optional()
    })
    .default({}),
  working: z.array(RecentItemSchema).default([]),
  episodic_hits: z.array(EpisodicRefSchema).default([]),
  semantic_profile: SemanticProfileSchema.default({
    traits: {},
    preferences: {},
    values: []
  }),
  schedule_window: z
    .object({
      events: z.array(ScheduleEventSchema).default([]),
      free_blocks: z.array(FreeBlockSchema).default([])
    })
    .default({
      events: [],
      free_blocks: []
    }),
  goals: z
    .object({
      short_term: z.array(z.string()).default([]),
      long_term: z.array(z.string()).default([])
    })
    .default({ short_term: [], long_term: [] }),
  constraints: z
    .object({
      quiet_hours: z.array(z.tuple([z.string(), z.string()])).optional(),
      do_not_disturb: z.boolean().optional(),
      energy_guards: z.array(z.string()).optional()
    })
    .default({}),
  tokens_estimate: z.number().nonnegative().optional()
});

/**
 * Plan graph
 */
export const TaskDraftSchema = z.object({
  title: z.string(),
  due: z.string().optional(),
  notes: z.string().optional(),
  tags: z.array(z.string()).optional()
});

export const BlockDraftSchema = z.object({
  title: z.string(),
  start: z.string().optional(),
  duration_minutes: z.number().int().positive().optional(),
  window: z.tuple([z.string(), z.string()]).optional()
});

export const NudgeDraftSchema = z.object({
  title: z.string(),
  send_at: z.string().optional(),
  channel: ChannelEnum.optional()
});

export const PlanStepSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("reflection"),
    text_template: z.string()
  }),
  z.object({
    type: z.literal("question"),
    target: z.enum(["person", "activity"]),
    purpose: z.enum(["confirm", "learn"]),
    template: z.string()
  }),
  z.object({
    type: z.literal("action.create"),
    payload: TaskDraftSchema
  }),
  z.object({
    type: z.literal("calendar.block.propose"),
    payload: BlockDraftSchema
  }),
  z.object({
    type: z.literal("nudge.schedule"),
    payload: NudgeDraftSchema
  })
]);

export const PlanGraphSchema = z.object({
  schema_version: SchemaVersionField,
  objective_now: ObjectiveEnum,
  learning_goal: z
    .object({
      hypothesis: z.string().optional(),
      micro_question: z.string().optional()
    })
    .optional(),
  steps: z.array(PlanStepSchema),
  followup_window: z
    .object({
      when: z.string(),
      reason: z.string().optional()
    })
    .optional()
});

/**
 * Memory records
 */
export const ShortTermInteractionSchema = z.object({
  schema_version: SchemaVersionField,
  id: z.string(),
  timestamp: z.string(),
  message: MessageSchema,
  facets: z.array(FacetSchema).default([]),
  deltas: z.record(z.unknown()).optional()
});

export const EpisodicRecordSchema = z.object({
  schema_version: SchemaVersionField,
  id: z.string(),
  when: z.string(),
  text: z.string(),
  facets: z.array(FacetSchema).default([]),
  embedding: z.array(z.number()).optional(),
  outcome: z.string().optional(),
  links: z.array(z.string()).optional(),
  provenance: z
    .array(
      z.object({
        source_id: z.string(),
        span: SpanSchema.optional()
      })
    )
    .default([])
});

export const EvidenceSchema = z.object({
  source_id: z.string(),
  span: SpanSchema.optional(),
  noted_at: z.string().optional()
});

export const SemanticTraitSchema = z.object({
  schema_version: SchemaVersionField,
  key: z.string(),
  value: z.unknown(),
  confidence: z.number().min(0).max(1),
  first_seen: z.string(),
  last_updated: z.string(),
  evidence: z.array(EvidenceSchema).default([])
});

export const PreferenceRecordSchema = z.object({
  schema_version: SchemaVersionField,
  key: z.string(),
  value: z.unknown(),
  scope: z.enum(["tone", "time", "workstyle", "health", "learning", "other"]).default("other"),
  confidence: z.number().min(0).max(1),
  first_seen: z.string(),
  last_updated: z.string(),
  evidence: z.array(EvidenceSchema).default([])
});

export const IdentityEdgeSchema = z.object({
  schema_version: SchemaVersionField,
  from: z.string(),
  to: z.string(),
  relationship: z.string(),
  strength: z.number().min(0).max(1).optional(),
  recency: z.string().optional()
});

export type Message = z.infer<typeof MessageSchema>;
export type Facet = z.infer<typeof FacetSchema>;
export type PersonFacet = z.infer<typeof PersonFacetSchema>;
export type ActivityFacet = z.infer<typeof ActivityFacetSchema>;
export type ContextPack = z.infer<typeof ContextPackSchema>;
export type PlanGraph = z.infer<typeof PlanGraphSchema>;
export type PlanStep = z.infer<typeof PlanStepSchema>;
export type TaskDraft = z.infer<typeof TaskDraftSchema>;
export type BlockDraft = z.infer<typeof BlockDraftSchema>;
export type NudgeDraft = z.infer<typeof NudgeDraftSchema>;
export type ShortTermInteraction = z.infer<typeof ShortTermInteractionSchema>;
export type EpisodicRecord = z.infer<typeof EpisodicRecordSchema>;
export type SemanticTrait = z.infer<typeof SemanticTraitSchema>;
export type PreferenceRecord = z.infer<typeof PreferenceRecordSchema>;
export type IdentityEdge = z.infer<typeof IdentityEdgeSchema>;

import type {
  ContextPack,
  Facet,
  Message,
  PlanGraph,
  ShortTermInteraction,
  EpisodicRecord,
  SemanticTrait,
  PreferenceRecord
} from "@sakhi/contracts";

export type DomainEvents = {
  "message.ingested": {
    message: Message;
  };
  "facet.extracted": {
    message_id: string;
    facets: Facet[];
  };
  "context.ready": {
    message_id: string;
    context: ContextPack;
  };
  "plan.ready": {
    message_id: string;
    context: ContextPack;
    plan: PlanGraph;
    extras?: Record<string, unknown>;
  };
  "reply.rendered": {
    message_id: string;
    plan_id?: string;
    response: {
      text: string;
      tone: string;
      metadata?: Record<string, unknown>;
    };
  };
  "action.routed": {
    message_id: string;
    plan_id?: string;
    tasks?: Array<{ id?: string; title: string; due?: string }>;
    blocks?: Array<{ id?: string; title: string; start?: string; duration_minutes?: number }>;
    nudges?: Array<{ id?: string; title: string; send_at?: string }>;
  };
  "memory.updated": {
    message_id: string;
    short_term?: ShortTermInteraction;
    episodic?: EpisodicRecord;
    traits?: SemanticTrait[];
    preferences?: PreferenceRecord[];
  };
};

export type DomainEventName = keyof DomainEvents;

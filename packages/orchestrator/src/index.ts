import type { Facet } from "@sakhi/contracts";
import { defaultEventBus, type DomainEvents, type DomainEventName } from "@sakhi/event-bus";
import type { WorkingContextBuilder } from "@sakhi/context-builder";
import type { RuleBasedPlanner } from "@sakhi/planner";
import type { PlannerInput } from "@sakhi/planner";

type FacetProvider = (messageId: string) => Promise<Facet[]>;

export type OrchestratorDeps = {
  eventBus?: typeof defaultEventBus;
  contextBuilder: WorkingContextBuilder;
  planner: RuleBasedPlanner;
  getFacets: FacetProvider;
};

export class ConversationOrchestrator {
  private readonly bus;
  private readonly contextBuilder;
  private readonly planner;
  private readonly getFacets;

  constructor({ eventBus = defaultEventBus, contextBuilder, planner, getFacets }: OrchestratorDeps) {
    this.bus = eventBus;
    this.contextBuilder = contextBuilder;
    this.planner = planner;
    this.getFacets = getFacets;
  }

  start() {
    this.bus.subscribe("message.ingested", async ({ message }) => {
      const facets = await this.getFacets(message.id);
      await this.bus.publish("facet.extracted", { message_id: message.id, facets });

      const context = await this.contextBuilder.build({
        userId: message.user_id,
        turnId: message.id,
        message,
        now: new Date(message.timestamp)
      });
      await this.bus.publish("context.ready", { message_id: message.id, context });

      const plannerInput: PlannerInput = { messageId: message.id, context, facets };
      const { plan, extras } = await this.planner.plan(plannerInput);
      await this.bus.publish("plan.ready", { message_id: message.id, context, plan, extras });
    });
  }
}

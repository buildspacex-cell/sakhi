import { defaultEventBus } from "@sakhi/event-bus";
import type { DomainEvents } from "@sakhi/event-bus";
import type { PlanGraph } from "@sakhi/contracts";

export type ActionRouterDeps = {
  eventBus?: typeof defaultEventBus;
  createTask?: (payload: { title: string; due?: string; notes?: string }, context: { userId: string; messageId: string }) => Promise<void>;
  proposeBlock?: (payload: { title: string; start?: string; duration_minutes?: number }) => Promise<void>;
  scheduleNudge?: (payload: { title: string; send_at?: string }) => Promise<void>;
};

export class ActionRouter {
  private readonly bus;
  private readonly createTask;
  private readonly proposeBlock;
  private readonly scheduleNudge;

  constructor({ eventBus = defaultEventBus, createTask, proposeBlock, scheduleNudge }: ActionRouterDeps) {
    this.bus = eventBus;
    this.createTask = createTask ?? (async () => {});
    this.proposeBlock = proposeBlock ?? (async () => {});
    this.scheduleNudge = scheduleNudge ?? (async () => {});
  }

  start() {
    this.bus.subscribe("plan.ready", async ({ message_id, plan, context }) => {
      await this.processPlan(message_id, plan, context.user_id);
    });
  }

  private async processPlan(messageId: string, plan: PlanGraph, userId: string) {
    const actionPayload: DomainEvents["action.routed"] = {
      message_id: messageId,
      plan_id: undefined,
      tasks: [],
      blocks: [],
      nudges: []
    };

    for (const step of plan.steps) {
      if (step.type === "action.create") {
        await this.createTask(step.payload, { userId, messageId });
        actionPayload.tasks?.push({ title: step.payload.title, due: step.payload.due });
      } else if (step.type === "calendar.block.propose") {
        await this.proposeBlock(step.payload);
        actionPayload.blocks?.push({ title: step.payload.title, start: step.payload.start });
      } else if (step.type === "nudge.schedule") {
        await this.scheduleNudge(step.payload);
        actionPayload.nudges?.push({ title: step.payload.title, send_at: step.payload.send_at });
      }
    }

    if ((actionPayload.tasks?.length ?? 0) || (actionPayload.blocks?.length ?? 0) || (actionPayload.nudges?.length ?? 0)) {
      await this.bus.publish("action.routed", actionPayload);
    }
  }
}

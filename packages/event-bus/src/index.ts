import type { DomainEvents, DomainEventName } from "./events";

type Handler<E extends DomainEventName> = (payload: DomainEvents[E]) => void | Promise<void>;

export interface Subscription {
  unsubscribe: () => void;
}

export class EventBus {
  private handlers: Map<DomainEventName, Set<Handler<any>>> = new Map();

  subscribe<E extends DomainEventName>(name: E, handler: Handler<E>): Subscription {
    const existing = this.handlers.get(name) ?? new Set();
    existing.add(handler as Handler<any>);
    this.handlers.set(name, existing);

    return {
      unsubscribe: () => existing.delete(handler as Handler<any>)
    };
  }

  async publish<E extends DomainEventName>(name: E, payload: DomainEvents[E]): Promise<void> {
    const listeners = new Set(this.handlers.get(name));
    for (const handler of listeners) {
      try {
        await handler(payload);
      } catch (err) {
        console.error(`[event-bus] handler for ${name} failed`, err);
      }
    }
  }

  clear(): void {
    this.handlers.clear();
  }
}

export const defaultEventBus = new EventBus();

export * from "./events";

import http from "node:http";
import { defaultEventBus } from "@sakhi/event-bus";
import { SimpleFacetExtractor, LLMFacetExtractor } from "@sakhi/facet-extractor";
import { WorkingContextBuilder } from "@sakhi/context-builder";
import type { MemoryStore } from "@sakhi/context-builder";
import { RuleBasedPlanner } from "@sakhi/planner";
import { ConversationOrchestrator } from "@sakhi/orchestrator";
import { InMemoryMemoryService, PostgresMemoryService } from "@sakhi/memory-service";
import type { MemoryService } from "@sakhi/memory-service";
import { LearningEngine } from "@sakhi/learning-engine";
import { ActionRouter } from "@sakhi/action-router";
import { PolicyEngine, OpenRouterLLMRenderer } from "@sakhi/policy-engine";
import { InsightEngine } from "@sakhi/insight-engine";
import { InMemoryScheduleStore } from "@sakhi/context-builder/scheduleStore.mock";
import { StaticRhythmEngine } from "@sakhi/context-builder/rhythmEngine.mock";
import { MessageSchema, type Message } from "@sakhi/contracts";

const PORT = Number(process.env.EVENT_BRIDGE_PORT ?? 4310);

class MemoryStoreAdapter implements MemoryStore {
  constructor(private readonly memory: MemoryService) {}

  async getShortTermBuffer(userId: string, limit: number) {
    return this.memory.getShortTerm(userId, limit);
  }

  async getEpisodicHits(params: { userId: string; queryEmbedding?: number[]; textQuery?: string; limit: number }) {
    const records = await this.memory.searchEpisodic(params.userId, params.textQuery ?? "", params.limit);
    return records.map((record) => ({ ...record, relevance: undefined }));
  }

  async getSemanticProfile(userId: string) {
    const traits = await this.memory.listSemanticTraits(userId);
    const preferences = await this.memory.listPreferences(userId);
    return {
      traits: Object.fromEntries(traits.map((t) => [t.key, t.value])),
      preferences: Object.fromEntries(preferences.map((p) => [`${p.scope}.${p.key}`, p.value])),
      values: []
    };
  }
}

const DATABASE_URL = process.env.MEMORY_PG_URL || process.env.DATABASE_URL;
const baseMemoryService: MemoryService = DATABASE_URL
  ? new PostgresMemoryService({ connectionString: DATABASE_URL })
  : new InMemoryMemoryService();
const memoryStore = new MemoryStoreAdapter(baseMemoryService);
const scheduleStore = new InMemoryScheduleStore();
const rhythmEngine = new StaticRhythmEngine();
const extractor = process.env.OPENROUTER_API_KEY
  ? new LLMFacetExtractor({ apiKey: process.env.OPENROUTER_API_KEY })
  : new SimpleFacetExtractor();
const messageCache = new Map<string, Message>();

const contextBuilder = new WorkingContextBuilder({ memoryStore, scheduleStore, rhythmEngine });
const planner = new RuleBasedPlanner();
const orchestrator = new ConversationOrchestrator({
  contextBuilder,
  planner,
  getFacets: async (messageId) => {
    const message = messageCache.get(messageId);
    if (!message) return [];
    const { facets } = await extractor.extract({ message });
    return facets;
  }
});

const learning = new LearningEngine({ memoryService: baseMemoryService, consolidationIntervalMs: 1000 * 60 * 60, decayAfterDays: 10 });
learning.start();
const renderer = process.env.OPENROUTER_API_KEY
  ? new OpenRouterLLMRenderer({ apiKey: process.env.OPENROUTER_API_KEY })
  : undefined;
const policy = new PolicyEngine({ renderer });
policy.start();
const insightEngine = new InsightEngine(baseMemoryService);

const TASK_ENDPOINT = process.env.TASK_ENDPOINT_URL;

const router = new ActionRouter({
  createTask: async (payload, ctx) => {
    if (!TASK_ENDPOINT) {
      console.log("[task.create]", payload);
      return;
    }
    try {
      await fetch(TASK_ENDPOINT, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: payload.title,
          description: payload.notes,
          due_at: payload.due,
          user_id: ctx.userId,
          related_entry_id: ctx.messageId.startsWith("journal:") ? ctx.messageId.split(":")[1] : undefined
        })
      });
    } catch (err) {
      console.error("Failed to persist task", err);
    }
  },
  proposeBlock: async (payload) => {
    console.log("[calendar.block]", payload);
  },
  scheduleNudge: async (payload) => {
    console.log("[nudge.schedule]", payload);
  }
});
router.start();

orchestrator.start();

defaultEventBus.subscribe("facet.extracted", ({ facets }) => {
  console.log("facets:", facets);
});
defaultEventBus.subscribe("context.ready", ({ context }) => {
  console.log("context ready:", context.turn_id);
});
defaultEventBus.subscribe("plan.ready", ({ plan }) => {
  console.log("plan:", plan.objective_now, plan.steps.length);
});
defaultEventBus.subscribe("action.routed", (payload) => {
  console.log("actions routed:", payload);
});
defaultEventBus.subscribe("reply.rendered", ({ response }) => {
  console.log("reply:", response);
});

function ensureScheduleWindow(userId: string) {
  scheduleStore.setWindow?.(userId, {
    events: [],
    freeBlocks: [
      {
        start: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
        end: new Date(Date.now() + 90 * 60 * 1000).toISOString(),
        energy: "high"
      }
    ]
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/events/message-ingested") {
    const raw = await readBody(req);
    try {
      const parsed = JSON.parse(raw || "{}");
      const messagePayload = parsed.message ?? parsed;
      const message = MessageSchema.parse(messagePayload);
      messageCache.set(message.id, message);
      ensureScheduleWindow(message.user_id);
      await defaultEventBus.publish("message.ingested", { message });
      res.writeHead(202, { "content-type": "application/json" });
      res.end(JSON.stringify({ status: "accepted" }));
    } catch (err) {
      console.error("Failed to process message.ingested payload", err);
      res.writeHead(400, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_payload" }));
    }
    return;
  }

  if (req.method === "POST" && req.url === "/insights/run") {
    const raw = await readBody(req);
    try {
      const parsed = JSON.parse(raw || "{}");
      const userId = parsed.user_id ?? "user-demo";
      const weekStart = parsed.week_start ? new Date(parsed.week_start) : startOfWeek(new Date());
      const insight = await insightEngine.synthesizeWeekly(userId, weekStart);
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(insight));
    } catch (err) {
      console.error("Failed to synthesize insights", err);
      res.writeHead(400, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_payload" }));
    }
    return;
  }

  res.writeHead(404, { "content-type": "application/json" });
  res.end(JSON.stringify({ error: "not_found" }));
});

server.listen(PORT, () => {
  console.log(`Event bridge listening on http://localhost:${PORT}/events/message-ingested`);
  console.log(`Insight endpoint at http://localhost:${PORT}/insights/run`);
});

function readBody(req: any): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: any[] = [];
    req.on("data", (chunk: any) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function startOfWeek(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  const day = copy.getDay();
  const diff = copy.getDate() - day + (day === 0 ? -6 : 1);
  copy.setDate(diff);
  return copy;
}

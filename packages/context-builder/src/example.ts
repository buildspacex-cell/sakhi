import { WorkingContextBuilder } from "./index";
import { InMemoryMemoryStore } from "./memoryStore.mock";
import { InMemoryScheduleStore } from "./scheduleStore.mock";
import { StaticRhythmEngine } from "./rhythmEngine.mock";
import { MessageSchema } from "@sakhi/contracts";

async function demo() {
  const memory = new InMemoryMemoryStore();
  const schedule = new InMemoryScheduleStore();
  const rhythms = new StaticRhythmEngine();

  const message = MessageSchema.parse({
    schema_version: "0.1.0",
    id: "msg-1",
    user_id: "user-1",
    timestamp: new Date().toISOString(),
    content: { text: "Feeling overwhelmed about tomorrow's review", modality: "text", locale: "en-US" },
    source: { channel: "web" },
    metadata: { timezone: "America/Los_Angeles" }
  });

  const builder = new WorkingContextBuilder({ memoryStore: memory, scheduleStore: schedule, rhythmEngine: rhythms });
  const pack = await builder.build({
    userId: message.user_id,
    turnId: "turn-1",
    message,
    now: new Date()
  });

  console.log(JSON.stringify(pack, null, 2));
}

demo().catch(console.error);

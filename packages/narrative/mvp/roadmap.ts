export const roadmap = {
  meta: {
    title: "Sakhi Roadmap",
    description: "Narrative roadmap demo for Sakhi",
  },
  hero: {
    title: "AI that compounds with use.",
    description:
      "Sakhi builds a longitudinal model of your decisions, actions, and patterns, so each interaction starts with more context than the last.",
    supportingLine: "Not a chatbot. A continuity system for how a life unfolds.",
    stats: [
      { label: "Core idea", value: "Tracks how a person evolves over time" },
      {
        label: "Primary motion",
        value: "Learns from action, outcome, and return",
      },
      { label: "Surface", value: "Built for clarity, reflection, and use" },
    ],
  },
  focus: {
    eyebrow: "Thesis",
    title: "Most AI answers a prompt. Sakhi builds continuity.",
    paragraphs: [
      "Today's AI resets every conversation.",
      "Sakhi does not.",
      "It connects decisions across time, learns from real outcomes, and keeps building a model of what is actually changing in a person's life.",
      "That creates a closed loop:",
      "understanding -> action -> outcome -> learning",
      "The more it is used, the more grounded, personal, and useful it becomes.",
    ],
  },
  loop: {
    title: "Continuity -> Intelligence -> Execution -> Learning Loop",
    description:
      "Each turn is treated as a cycle: capture the signal, shape it with continuity, execute a response, then feed the result back into the model.",
    steps: [
      {
        title: "User Input",
        detail: "Intent, emotion, and context arrive together in one stream.",
      },
      {
        title: "Continuity Engine (Kala)",
        detail: "The deterministic layer preserves arc, history, and policy.",
      },
      {
        title: "Sakhi Intelligence",
        detail: "The reasoning layer narrows what matters right now.",
      },
      {
        title: "Execution Layer",
        detail: "The system routes, composes, and delivers a response.",
      },
      {
        title: "Action / Output",
        detail: "The user acts on the response in the real world.",
      },
      {
        title: "Outcome Capture",
        detail: "Signal from the outcome is collected for the next pass.",
      },
      {
        title: "Feedback -> Continuity",
        detail: "The next turn starts with a better model of the person.",
      },
    ],
  },
  storyPanel: {
    eyebrow: "Why this shape",
    title: "The product is framed as a loop, not a one-off feature list.",
    body: "The deck stays reusable because the roadmap content lives in the narrative package. The page only renders the data and components.",
    notes: [
      {
        title: "Reusable content model",
        body: "The page consumes structured roadmap data, so future decks can swap in different narratives without changing layout code.",
      },
      {
        title: "Demo app contract",
        body: "The `/mvp` route is a presentation shell. It does not own the story text.",
      },
    ],
  },
  phases: {
    title: "Phase map",
    description:
      "The roadmap is grouped into six moves so the demo can explain scope without losing the narrative thread.",
    items: [
      {
        title: "Continuity Foundation",
        detail: "Topic threads, arc building, Deep Reflect, and Kala governance.",
        note: "Foundational",
      },
      {
        title: "Intelligence Layer",
        detail: "Intent detection, probing, context shaping, and response control.",
        note: "Reasoning",
      },
      {
        title: "Execution Layer",
        detail: "LLM aggregation, routing, and structured prompt orchestration.",
        note: "Delivery",
      },
      {
        title: "Outcome Capture",
        detail: "Track actions, decisions, and feedback signals after the turn.",
        note: "Telemetry",
      },
      {
        title: "Learning System",
        detail: "Behavior patterns, success and failure learning, and adaptation.",
        note: "Memory",
      },
      {
        title: "Expansion Layer",
        detail: "Health, finance, decision systems, and Sakhi Network surfaces.",
        note: "Growth",
      },
    ],
  },
  futureSections: [
    {
      id: "vision",
      label: "Vision",
      eyebrow: "Future section",
      title: "Sakhi becomes the layer that holds a person's longitudinal context.",
      description:
        "The cinematic system can now expand beyond the roadmap into durable story chapters without changing the page shell.",
      body: "Vision sections should feel like product conviction, not filler slides. The narrative package owns that content, and the demo shell just stages it with motion, pacing, and contrast.",
      points: [
        "The demo is now section-driven, so new story chapters can be added from content data instead of ad hoc page markup.",
        "Each future section inherits the same full-screen snap behavior, premium framing, and scroll rhythm as the core roadmap.",
        "This keeps the presentation extensible for founder story, product thesis, and strategic framing.",
      ],
    },
    {
      id: "moat",
      label: "Moat",
      eyebrow: "Future section",
      title: "The moat is compounding continuity, not one more model wrapper.",
      description:
        "Sakhi gets stronger as the loop accumulates signal across memory, governance, decisions, and feedback.",
      body: "A cinematic section on moat needs to show why the system is hard to copy: the power comes from the integrated loop, not a single prompt or interface flourish.",
      points: [
        "Continuity preserves what matters across time instead of treating every turn as stateless chat.",
        "Governance constrains behavior so the system can grow without becoming noisy or unsafe.",
        "Outcome capture turns real-world follow-through into future intelligence, which compounds the product advantage.",
      ],
    },
    {
      id: "product",
      label: "Product",
      eyebrow: "Future section",
      title: "Product surfaces can keep evolving while the narrative engine stays stable.",
      description:
        "The same story shell can frame roadmap, product vision, go-to-market, or investor narrative without rewiring the cinematic primitives.",
      body: "That separation matters. The presentation system should be reusable enough to support new sections and new stories, while the components continue to deliver the same polished motion and layout behavior.",
      points: [
        "Section wrappers, glass panels, and progress tracking now work as reusable storytelling primitives.",
        "Narrative content stays in the package layer, which keeps the page modular and easier to maintain.",
        "The demo can expand into product, moat, and vision chapters without losing pacing or design coherence.",
      ],
    },
  ],
  closing: {
    eyebrow: "Why it matters",
    title: "The system improves every loop.",
    description: "The deck closes on the same principle the product uses to learn.",
    body: "Sakhi builds a longitudinal model of how a person thinks, acts, and evolves. Each pass through the loop sharpens the next response, and the roadmap makes that motion visible without hardcoding the story into the page.",
  },
} as const;

export default roadmap;

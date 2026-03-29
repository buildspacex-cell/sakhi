"use client";

import { PhaseGrid } from "@/components/mvp/PhaseGrid";
import AnimatedLoop from "@/components/story/AnimatedLoop";
import ArchitectureSection from "@/components/story/ArchitectureSection";
import CommunicationContinuitySection from "@/components/story/CommunicationContinuitySection";
import IntroScene from "@/components/story/IntroScene";
import ProductFlowSection from "@/components/story/ProductFlowSection";
import ResetCollapseScene from "@/components/story/ResetCollapseScene";
import ScrollScene from "@/components/story/ScrollScene";
import Section from "@/components/story/Section";
import StoryScrollContainer from "@/components/story/StoryScrollContainer";
import ThoughtField from "@/components/story/ThoughtField";
import { roadmap } from "@narrative/mvp/roadmap";

const problemLines = [
  "It never really stops.",
  "And it doesn't carry forward.",
  "Nothing actually holds it together.",
] as const;

const resetPoints = [
  "Thoughts reset",
  "Good ideas die",
  "Continuity is lost",
] as const;

const solutionPoints = [
  "Remembers what you share",
  "Connects it over time",
  "Learns from real outcomes",
] as const;

const productScenes = [
  {
    eyebrow: "Start talking",
    title: "Conversation becomes a living thread.",
    description:
      "Start anywhere. Sakhi keeps the thread, the context, and the momentum intact.",
    caption: "Conversation is no longer a disposable prompt-response exchange.",
    imageSrc: "/story/chat.png",
  },
  {
    eyebrow: "Reflection",
    title: "Your life becomes visible.",
    description:
      "Patterns stop feeling abstract when attention, energy, and tension start surfacing as real threads.",
    caption: "Reflection turns scattered experience into something you can actually see.",
    imageSrc: "/story/reflection.png",
  },
  {
    eyebrow: "Moments",
    title: "Your story starts to take shape.",
    description:
      "What you have lived stays connected, forming a timeline you can return to and build on.",
    caption: "Moments accumulate into continuity instead of disappearing into history.",
    imageSrc: "/story/moments.png",
  },
  {
    eyebrow: "Insights",
    title: "Every insight stays grounded.",
    description:
      "The system can always point back to the lived moment behind the pattern, not just the conclusion.",
    caption: "Insight stays explainable because the evidence behind it is always there.",
    imageSrc: "/story/insights.png",
  },
] as const;

const loopSteps = [
  {
    title: "Understanding",
    detail: "Capture the user's signal, context, and intent as one evolving thread.",
  },
  {
    title: "Action",
    detail: "Respond, reflect, or guide in a way that can shape what happens next.",
  },
  {
    title: "Outcome",
    detail: "Observe what changed in the real world, not just what was said in chat.",
  },
  {
    title: "Learning",
    detail: "Update the model so future responses are more grounded and more personal.",
  },
] as const;

const introStats = [
  {
    value: "Builds a living model of you. It evolves over time.",
  },
  {
    value: "Makes your life visible. Across time, as a whole.",
  },
  {
    value: "Helps you act decisively. It learns from what follows.",
  },
] as const;

const architecturePillars = [
  {
    system: "Sakhi",
    stage: "Listening and sensing layer",
    title: "Builds a living model of you. It evolves over time.",
    summary:
      "This is the listening, conversation, sensing, and surfacing layer. Sakhi is where life is received, where context is felt, and where the system returns something usable to the person.",
    existsNow: [
      "Receives journals, conversations, and active user input.",
      "Responds in conversation with continuity-aware context.",
      "Surfaces reflections, threads, and product experiences back to the user.",
      "Acts as the user-facing layer over memory and continuity.",
    ],
    visionHolds: [
      "Broader sensing across more life signals and passive context.",
      "A richer conversational layer that adapts to state, timing, and intent.",
      "A clearer product surface that makes the deeper system feel natural to use.",
    ],
    mvpFeatures: ["Conversation", "Reflection", "Moments", "Insights"],
    visionFeatures: ["Passive sensing", "Adaptive conversation", "Context-aware reflection", "Unified life surfaces"],
    captures: ["Journals", "Conversations", "Events", "Future passive signals"],
    builds: ["Input layer", "Conversation layer", "Reflection surfaces", "User-facing product shell"],
    computes: [
      "State sensing",
      "Context framing",
      "Response adaptation",
      "Surface selection",
    ],
    surfaces: ["Conversation", "Reflection", "Continuity views", "Action prompts"],
  },
  {
    system: "Kala",
    stage: "Continuity engine",
    title: "Makes your life visible. Across time, as a whole.",
    summary:
      "This is the continuity layer. Kala connects moments across time so life can be seen as threads, arcs, and grounded reflection instead of fragments.",
    existsNow: [
      "Connects entries across time into continuity threads.",
      "Builds topic arcs from repeated signals and moments.",
      "Links related threads across contexts.",
      "Enables deep reflection over accumulated continuity.",
      "Produces structured synthesis from lived history.",
    ],
    visionHolds: [
      "Stronger temporal linking across more life signals.",
      "Richer arc formation and recurring-loop explainability.",
      "A more stable continuity engine beneath every future surface.",
    ],
    mvpFeatures: ["Continuity threads", "Deep Reflect", "Topic arcs", "Weekly synthesis"],
    visionFeatures: ["Cross-thread continuity", "Long-range arc builder", "Loop explainability", "Continuity graph"],
    captures: ["Episodes", "Topics", "Rhythms", "Recurring signals"],
    builds: ["Timeline view", "Topic threads", "Weekly synthesis", "Monthly synthesis"],
    computes: ["Pattern detection", "Behavior loops", "Energy trends", "Grounded reflection"],
    surfaces: ["Topic bubbles", "Timeline arcs", "Density mapping", "Evidence-backed insight"],
  },
  {
    system: "Karma",
    stage: "Action layer",
    title: "Helps you act decisively. It learns from what follows.",
    summary:
      "This is the action layer. Karma is where clarity turns into action, where Sakhi connects outward to agents and other Sakhis, and where outcomes feed back into continuity.",
    existsNow: [],
    visionHolds: [
      "A true intention → action → outcome → learning loop.",
      "Direct connection to external agents and execution systems.",
      "Connection to other Sakhis for coordinated action across people.",
      "Stronger outcome capture that updates continuity and the personal model.",
    ],
    mvpFeatures: [],
    visionFeatures: ["Action handoffs", "Agent orchestration", "Sakhi network", "Outcome learning"],
    visionOnly: true,
    captures: ["Decisions", "Goals", "Actions taken", "Outcomes"],
    builds: ["Planner state", "Action layer", "Agent links", "Outcome record"],
    computes: ["Tradeoff framing", "Execution routing", "Intention versus outcome", "Feedback loop"],
    surfaces: ["Action prompts", "Agent handoffs", "Sakhi-to-Sakhi coordination", "Improved future clarity"],
  },
] as const;

function ProblemLine({
  text,
  isLast,
}: {
  text: string;
  isLast: boolean;
}) {
  return (
    <p
      className={`text-balance text-[1.22rem] leading-[1.42] tracking-[-0.022em] sm:text-[1.45rem] ${
        isLast ? "text-slate-100" : "text-[#c9d3ea]"
      }`}
    >
      {text}
    </p>
  );
}

function SolutionItem({
  text,
}: {
  text: string;
}) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,22,32,0.9),rgba(10,13,19,0.94))] px-6 py-8 text-left shadow-panel">
      <div className="text-[10px] font-semibold uppercase tracking-[0.3em] text-[#c4d2ff]">
        Action
      </div>
      <p className="mt-5 text-2xl font-medium leading-[1.35] tracking-[-0.03em] text-white">
        {text}
      </p>
    </div>
  );
}

export default function StoryPage() {
  return (
    <main className="relative isolate bg-[#0f1115] text-slate-50">
      <StoryScrollContainer id="web-story-scroll">
        <Section id="intro" className="pt-20 lg:pt-24">
          <IntroScene stats={introStats} />
        </Section>

        <Section id="problem">
          <ScrollScene className="mx-auto max-w-6xl">
            <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.85fr)] lg:gap-16">
              <div className="text-center lg:text-left">
                <h2 className="mx-auto max-w-[14ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:mx-0 lg:text-6xl">
                  There&apos;s a conversation happening in your head.
                </h2>

                <div className="relative mx-auto mt-10 max-w-2xl lg:mx-0">
                  <div className="absolute left-[-1.5rem] top-3 h-24 w-24 rounded-full bg-[#8aa3ff]/12 blur-3xl" />
                  <div className="absolute inset-y-1 left-0 w-px bg-gradient-to-b from-transparent via-white/28 to-transparent" />
                  <div className="relative space-y-4 pl-6 sm:space-y-5 sm:pl-8">
                    {problemLines.map((line) => (
                      <div key={line}>
                        <ProblemLine
                          text={line}
                          isLast={line === problemLines[problemLines.length - 1]}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mx-auto w-full max-w-[26rem]">
                <ThoughtField />
              </div>
            </div>
          </ScrollScene>
        </Section>

        <Section id="reset">
          <ResetCollapseScene lines={resetPoints} />
        </Section>

        <Section id="solution">
          <ScrollScene className="mx-auto max-w-5xl text-center" fromY={44} toY={-24}>
            <h2 className="mx-auto max-w-[14ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
              Sakhi makes it all come together.
            </h2>

            <div className="mx-auto mt-8 max-w-3xl space-y-5">
              <p className="text-balance text-[1.35rem] leading-[1.38] tracking-[-0.03em] text-[#d5ddf4] sm:text-[1.65rem]">
                You do not have to be driven by your thoughts.
              </p>
              <p className="text-balance text-[1.18rem] leading-[1.5] tracking-[-0.025em] text-slate-300 sm:text-[1.35rem]">
                You can shape them.
              </p>
            </div>

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {solutionPoints.map((point) => (
                <SolutionItem
                  key={point}
                  text={point}
                />
              ))}
            </div>
          </ScrollScene>
        </Section>

        <Section id="shaping" className="pt-8 lg:pt-12">
          <IntroScene stats={introStats} />
        </Section>

        <Section id="product" className="py-10">
          <ScrollScene className="space-y-8" fromY={46} toY={-30}>
            <div className="max-w-4xl">
              <h2 className="max-w-[13ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
                Emotional continuity becomes a usable product.
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                The interface moves from conversation to reflection to
                evidence-backed insight without breaking the thread.
              </p>
            </div>

            <ProductFlowSection scenes={productScenes} />
          </ScrollScene>
        </Section>

        <Section id="architecture" className="py-10">
          <ScrollScene className="space-y-8" fromY={42} toY={-22}>
            <ArchitectureSection pillars={architecturePillars} />
          </ScrollScene>
        </Section>

        <Section id="communication" className="py-10">
          <ScrollScene className="space-y-8" fromY={42} toY={-22}>
            <CommunicationContinuitySection />
          </ScrollScene>
        </Section>

        <Section id="roadmap" className="py-10">
          <ScrollScene className="space-y-8" fromY={42} toY={-22}>
            <div className="max-w-4xl">
              <h2 className="max-w-[12ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
                Then the system becomes a rollout.
              </h2>
              <p className="mt-4 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                Once the MVP and the architecture are clear, the next question
                is sequencing. These are the staged moves that turn the current
                product into the fuller system.
              </p>
            </div>

            <PhaseGrid
              title={roadmap.phases.title}
              description={roadmap.phases.description}
              phases={roadmap.phases.items}
              className="w-full"
            />
          </ScrollScene>
        </Section>

        <Section id="system" className="py-10">
          <ScrollScene className="space-y-8" fromY={38} toY={-18}>
            <AnimatedLoop
              title="UNDERSTANDING → ACTION → OUTCOME → LEARNING"
              description="This is the core system loop. Each interaction shapes what Sakhi understands, what it does next, and what it learns from the result."
              steps={loopSteps}
            />
          </ScrollScene>
        </Section>

        <Section id="close">
          <ScrollScene className="mx-auto max-w-4xl text-center" fromY={30} toY={0}>
            <h2 className="mx-auto max-w-[15ch] text-4xl font-semibold leading-[1.05] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
              When technology learns how you think, the mental load finally
              lifts.
            </h2>
          </ScrollScene>
        </Section>

        <Section id="cta">
          <ScrollScene
            className="mx-auto max-w-4xl rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(18,23,33,0.92),rgba(10,13,20,0.96))] px-6 py-10 text-center shadow-panel sm:px-10 sm:py-12"
            fromY={20}
            toY={0}
          >
            <h2 className="mx-auto max-w-[12ch] text-4xl font-semibold leading-[1.02] tracking-[-0.05em] text-white sm:text-5xl lg:text-6xl">
              This is just the beginning.
            </h2>
            <p className="mt-5 text-lg leading-8 text-slate-300 sm:text-xl">
              Use it. Break it. Shape it.
            </p>
          </ScrollScene>
        </Section>
      </StoryScrollContainer>
    </main>
  );
}

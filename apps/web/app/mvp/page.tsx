import type { Metadata } from "next";

import ScrollContainer from "@/components/mvp/ScrollContainer";
import ScrollProgress from "@/components/mvp/ScrollProgress";
import { Slide } from "@/components/mvp/Slide";
import { LoopDiagram } from "@/components/mvp/LoopDiagram";
import { PhaseGrid } from "@/components/mvp/PhaseGrid";
import { roadmap } from "@narrative/mvp/roadmap";

const introStats = [
  { label: "Core idea", value: "Builds a model of how you evolve" },
  { label: "Primary motion", value: "Improves through real-world feedback" },
  { label: "Surface", value: "Designed for clarity and reflection" },
] as const;

export const metadata: Metadata = {
  title: roadmap.meta.title,
  description: roadmap.meta.description,
};

export default function MvpPage() {
  return (
    <main className="relative isolate bg-[#0f1115] text-slate-50">
      <ScrollContainer id="web-mvp-story-scroll">
        <ScrollProgress containerId="web-mvp-story-scroll" />

        <div className="relative mx-auto w-full max-w-7xl px-5 sm:px-8 lg:px-12">
        <Slide
          id="intro"
          label="Intro"
          title="AI that learns how you evolve."
          description="Sakhi builds a longitudinal model of your decisions, actions, and patterns — so every interaction improves the next one."
          className="shadow-panel"
          titleClassName="max-w-[8ch] text-[3.6rem] leading-[0.96] tracking-[-0.075em] sm:text-[4.8rem] lg:text-[5.15rem]"
          descriptionClassName="max-w-[17ch] text-[1.08rem] leading-[1.5] sm:text-[1.28rem] sm:leading-[1.48]"
        >
          <div className="w-full rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,21,29,0.78),rgba(13,16,22,0.9))] p-5 shadow-panel sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-500">
                System properties
              </div>
              <div className="h-px flex-1 bg-white/10" />
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {introStats.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-[28px] border border-white/10 bg-[#10141c]/88 px-5 py-5 sm:min-h-[212px]"
                >
                  <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">
                    {stat.label}
                  </div>
                  <div className="mt-6 max-w-[11ch] text-[1.6rem] font-medium leading-[1.16] tracking-[-0.03em] text-white sm:text-[1.92rem]">
                    {stat.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Slide>

        <section
          id="loop"
          data-story-section="true"
          data-story-label="Loop"
          className="grid min-h-[100svh] snap-start items-center gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]"
        >
            <LoopDiagram
              title={roadmap.loop.title}
              description={roadmap.loop.description}
              steps={roadmap.loop.steps}
            />
            <div className="rounded-[28px] border border-white/10 bg-[#121720]/80 p-6 shadow-panel">
              <div className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                {roadmap.storyPanel.eyebrow}
              </div>
              <div className="mt-4 text-2xl font-display font-semibold leading-tight text-white">
                {roadmap.storyPanel.title}
              </div>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                {roadmap.storyPanel.body}
              </p>

              <div className="mt-6 grid gap-3">
                {roadmap.storyPanel.notes.map((note) => (
                  <div
                    key={note.title}
                    className="rounded-2xl border border-white/8 bg-white/4 px-4 py-3"
                  >
                    <div className="text-sm font-medium text-white">{note.title}</div>
                    <div className="mt-1 text-sm leading-6 text-slate-300">{note.body}</div>
                  </div>
                ))}
              </div>
            </div>
        </section>

        <section
          id="roadmap"
          data-story-section="true"
          data-story-label="Roadmap"
          className="flex min-h-[100svh] snap-start items-center"
        >
          <PhaseGrid
            title={roadmap.phases.title}
            description={roadmap.phases.description}
            phases={roadmap.phases.items}
            className="w-full"
          />
        </section>

        {roadmap.futureSections.map((section) => (
          <Slide
            key={section.id}
            id={section.id}
            label={section.label}
            eyebrow={section.eyebrow}
            title={section.title}
            description={section.description}
          >
            <div className="rounded-[28px] border border-white/10 bg-white/4 p-6">
              <p className="text-sm leading-7 text-slate-300">{section.body}</p>
              <div className="mt-6 grid gap-3">
                {section.points.map((point, index) => (
                  <div
                    key={point}
                    className="rounded-[22px] border border-white/10 bg-[#121722]/78 px-4 py-4"
                  >
                    <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                      {String(index + 1).padStart(2, "0")}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-slate-200">{point}</div>
                  </div>
                ))}
              </div>
            </div>
          </Slide>
        ))}

        <Slide
          id="closing"
          label="Close"
          eyebrow={roadmap.closing.eyebrow}
          title={roadmap.closing.title}
          description={roadmap.closing.description}
          className="mb-2"
        >
          <div className="rounded-[28px] border border-white/10 bg-[#121720]/85 p-6">
            <div className="text-sm leading-7 text-slate-300">{roadmap.closing.body}</div>
          </div>
        </Slide>
        </div>
      </ScrollContainer>
    </main>
  );
}

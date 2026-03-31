import GlassCard from "@/components/cinematic/GlassCard";
import Section from "@/components/cinematic/Section";

type StoryNote = {
  title: string;
  body: string;
};

type StoryPanel = {
  eyebrow: string;
  title: string;
  body: string;
  notes: ReadonlyArray<StoryNote>;
};

type Phase = {
  title: string;
  detail: string;
  note?: string;
};

type RoadmapSectionProps = {
  id?: string;
  label?: string;
  title: string;
  description?: string;
  storyPanel: StoryPanel;
  phases: ReadonlyArray<Phase>;
};

export default function RoadmapSection({
  id,
  label,
  title,
  description,
  storyPanel,
  phases,
}: RoadmapSectionProps) {
  return (
    <Section id={id} label={label}>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
        <div className="flex flex-col justify-between gap-6">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">
              Roadmap
            </div>
            <h2 className="mt-4 font-display text-4xl font-semibold tracking-[-0.05em] text-white sm:text-5xl">
              {title}
            </h2>
            {description ? (
              <p className="mt-4 max-w-xl text-base leading-8 text-slate-300">
                {description}
              </p>
            ) : null}
          </div>

          <div className="rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,21,30,0.9),rgba(11,14,19,0.94))] p-6 shadow-panel">
            <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
              {storyPanel.eyebrow}
            </div>
            <h3 className="mt-4 font-display text-2xl font-semibold tracking-[-0.03em] text-white">
              {storyPanel.title}
            </h3>
            <p className="mt-4 text-sm leading-7 text-slate-300">{storyPanel.body}</p>

            <div className="mt-6 space-y-3">
              {storyPanel.notes.map((note) => (
                <div
                  key={note.title}
                  className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-4"
                >
                  <div className="text-sm font-medium text-white">{note.title}</div>
                  <div className="mt-1 text-sm leading-6 text-slate-300">
                    {note.body}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {phases.map((phase, index) => (
            <GlassCard
              key={phase.title}
              title={phase.title}
              description={phase.detail}
              eyebrow={phase.note}
              index={index}
            />
          ))}
        </div>
      </div>
    </Section>
  );
}

"use client";

type NoiseSignal = {
  text: string;
  x: number;
  y: number;
  tone?: "soft" | "bright";
  size?: "sm" | "md" | "lg";
};

type OccupancyBubble = {
  label: string;
  share: string;
  moments: string;
  width: string;
  height: string;
  left: string;
  top: string;
  accent?: boolean;
};

type StartupArcStage = {
  label: string;
  title: string;
  body: string;
  meta: string;
  emphasis?: "major" | "minor";
};

const continuityNoise: readonly NoiseSignal[] = [
  { text: "did I reply?", x: -610, y: -310, size: "md" },
  { text: "my daughter lost a close game", x: -420, y: -220, tone: "bright", size: "sm" },
  { text: "skip dinner again?", x: -720, y: -50, size: "sm" },
  { text: "Dad needs care", x: -560, y: 90, tone: "bright", size: "md" },
  { text: "work pressure", x: -360, y: 240, size: "md" },
  { text: "I forgot yoga", x: -670, y: 340, size: "md" },
  { text: "how do I say this clearly?", x: -110, y: -360, size: "lg" },
  { text: "too many tabs open", x: 90, y: -250, size: "md" },
  { text: "what keeps repeating?", x: 330, y: -310, tone: "bright", size: "sm" },
  { text: "boardroom intensity", x: 520, y: -140, size: "md" },
  { text: "call mom back", x: 700, y: -20, size: "sm" },
  { text: "family guilt", x: 650, y: 150, size: "sm" },
  { text: "I need to remember this", x: 470, y: 310, size: "md" },
  { text: "peace is available", x: 170, y: 360, tone: "bright", size: "sm" },
  { text: "what am I missing?", x: -50, y: 220, size: "sm" },
  { text: "another meeting", x: 720, y: 340, size: "sm" },
  { text: "dentist for mom", x: -760, y: -180, size: "sm" },
  { text: "pitch deck feedback", x: -250, y: -280, tone: "bright", size: "sm" },
  { text: "have I followed up?", x: -30, y: -190, size: "sm" },
  { text: "I need a clearer plan", x: 220, y: -130, tone: "bright", size: "md" },
  { text: "missed dinner with family", x: 770, y: 80, size: "sm" },
  { text: "when do I rest?", x: -770, y: 220, size: "sm" },
  { text: "motherhood feels like extension", x: -340, y: 175, tone: "bright", size: "sm" },
  { text: "too much mental load", x: 80, y: 290, size: "sm" },
  { text: "I need to get back to them", x: 260, y: 200, size: "md" },
  { text: "this feels urgent", x: 520, y: 230, tone: "bright", size: "sm" },
  { text: "not another reactive answer", x: -500, y: -150, size: "sm" },
  { text: "hold it all together", x: -300, y: 330, size: "sm" },
  { text: "will this actually help?", x: 10, y: 370, size: "sm" },
  { text: "I said I would revisit this", x: 690, y: -250, size: "sm" },
  { text: "coming back after a gap", x: 620, y: -340, size: "sm" },
  { text: "what thread is this really?", x: -700, y: 10, tone: "bright", size: "sm" },
  { text: "emails before sunrise", x: -290, y: -195, size: "sm" },
  { text: "caregiving softness", x: 420, y: 110, size: "sm" },
  { text: "short-term clarity", x: 380, y: -55, tone: "bright", size: "sm" },
  { text: "what did I promise?", x: -390, y: 30, size: "sm" },
] as const;

const occupancyBubbles: readonly OccupancyBubble[] = [
  {
    label: "Start up",
    share: "65%",
    moments: "28 moments",
    width: "19rem",
    height: "19rem",
    left: "31%",
    top: "42%",
    accent: true,
  },
  {
    label: "Family",
    share: "14%",
    moments: "6 moments",
    width: "11rem",
    height: "11rem",
    left: "72%",
    top: "22%",
  },
  {
    label: "Caregiving",
    share: "7%",
    moments: "3 moments",
    width: "8.9rem",
    height: "8.9rem",
    left: "52%",
    top: "68%",
  },
  {
    label: "Career",
    share: "7%",
    moments: "3 moments",
    width: "8.8rem",
    height: "8.8rem",
    left: "70%",
    top: "56%",
  },
  {
    label: "Self Care",
    share: "7%",
    moments: "3 moments",
    width: "8.8rem",
    height: "8.8rem",
    left: "86%",
    top: "39%",
  },
] as const;

const startupArcStages: readonly StartupArcStage[] = [
  {
    label: "Where It Began",
    title: "An idea with ache",
    body: "The thread began with one question: was this passing frustration, or the start of something to build?",
    meta: "Day 12",
    emphasis: "major",
  },
  {
    label: "Phase 1",
    title: "Founder question",
    body: "Could this become real?",
    meta: "Day 16",
    emphasis: "minor",
  },
  {
    label: "Phase 2",
    title: "Rhythm clicked",
    body: "Rhythm, not remedies.",
    meta: "Day 19",
    emphasis: "minor",
  },
  {
    label: "Phase 3",
    title: "RAG felt brittle",
    body: "The obvious path felt thin.",
    meta: "Day 24",
    emphasis: "minor",
  },
  {
    label: "Phase 4",
    title: "Knowledge graph",
    body: "Slower, more respectful.",
    meta: "Day 28",
    emphasis: "minor",
  },
  {
    label: "Phase 5",
    title: "Still uneasy",
    body: "Correct, but not personal.",
    meta: "Day 35",
    emphasis: "minor",
  },
  {
    label: "Phase 6",
    title: "Clarity surfaced",
    body: "Reflection became the job.",
    meta: "Day 41",
    emphasis: "minor",
  },
  {
    label: "Phase 7",
    title: "Validation pressure",
    body: "External pressure sharpened it.",
    meta: "Day 58",
    emphasis: "minor",
  },
  {
    label: "Phase 8",
    title: "Build, not pitch",
    body: "Usage had to prove it.",
    meta: "Day 66",
    emphasis: "minor",
  },
  {
    label: "Phase 9",
    title: "Continuity core",
    body: "The thread became the product.",
    meta: "Day 72",
    emphasis: "minor",
  },
  {
    label: "Phase 10",
    title: "Product shape",
    body: "The path finally had form.",
    meta: "Day 115",
    emphasis: "minor",
  },
  {
    label: "Where It Is Now",
    title: "A visible direction",
    body: "The thread is no longer abstract. It now has form, continuity, and a next step people can feel.",
    meta: "104 days of continuity",
    emphasis: "major",
  },
] as const;

function OccupancyBoard() {
  return (
    <div className="continuity-occupancy-board relative mx-auto w-full max-w-[62rem] overflow-hidden rounded-[40px] border border-white/[0.09] bg-[linear-gradient(158deg,rgba(12,17,30,0.98),rgba(7,10,20,0.96))] shadow-[0_52px_160px_rgba(0,0,0,0.52),inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-2xl">
      {/* Ambient color bleeds */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_15%_10%,rgba(110,148,230,0.14),transparent),radial-gradient(ellipse_50%_45%_at_88%_92%,rgba(105,78,55,0.12),transparent),radial-gradient(ellipse_40%_35%_at_82%_8%,rgba(120,148,210,0.08),transparent)]" />

      <div className="continuity-occupancy-shell relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between gap-5 border-b border-white/[0.06] px-7 pb-5 pt-6 sm:px-9 sm:pt-7">
          <div className="continuity-occupancy-copy">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
              <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />
              Vidhya · Profile
            </div>
            <div className="mt-3 text-[1.85rem] font-semibold tracking-[-0.055em] text-white sm:text-[2rem]">
              Life Occupancy
            </div>
            <p className="mt-1.5 max-w-[30rem] text-[0.9rem] leading-[1.65] tracking-[-0.015em] text-white/44">
              Bubble size reflects how much each thread has occupied your attention.
            </p>
          </div>

          <div className="shrink-0 rounded-2xl border border-white/[0.09] bg-white/[0.03] px-4 py-3 text-right backdrop-blur-sm">
            <div className="text-[9px] font-semibold uppercase tracking-[0.26em] text-white/30">Active</div>
            <div className="mt-1.5 text-[1.05rem] font-semibold tracking-[-0.04em] text-white/82">5 threads</div>
          </div>
        </div>

        {/* Bubble cloud */}
        <div className="continuity-bubble-cloud relative h-[26rem] overflow-visible px-2 sm:h-[28rem]">
          {/* Soft inner glow at top */}
          <div className="pointer-events-none absolute left-[22%] top-0 h-48 w-48 -translate-x-1/2 rounded-full bg-[#8cb7ff]/6 blur-3xl" />
          <div className="pointer-events-none absolute right-[18%] top-[30%] h-40 w-40 rounded-full bg-[#b0c8ff]/4 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 left-[10%] h-36 w-36 rounded-full bg-[#8b664d]/6 blur-3xl" />

          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 1000 580"
            fill="none"
            preserveAspectRatio="none"
          >
            {/* Arcs connecting main bubble to satellites */}
            <path d="M310 258C400 195 530 190 645 222" stroke="rgba(200,218,255,0.11)" strokeWidth="1.2" strokeLinecap="round" />
            <path d="M328 374C440 418 570 420 655 392" stroke="rgba(200,218,255,0.07)" strokeWidth="1.2" strokeLinecap="round" />
            <path d="M720 185C768 242 788 318 784 402" stroke="rgba(200,218,255,0.07)" strokeWidth="1" strokeDasharray="4 12" strokeLinecap="round" />
          </svg>

          {occupancyBubbles.map((bubble) => (
            <div
              key={bubble.label}
              className={`continuity-occupancy-bubble ${bubble.accent ? "continuity-startup-bubble" : ""} absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full text-center ${
                bubble.accent
                  ? "border border-[#dce8ff]/50 bg-[radial-gradient(circle_at_36%_28%,rgba(235,242,255,0.19),rgba(165,190,235,0.26)_48%,rgba(55,72,108,0.38)_100%)] shadow-[0_0_80px_rgba(148,178,255,0.16),0_24px_64px_rgba(0,0,0,0.38)]"
                  : "border border-white/[0.11] bg-[radial-gradient(circle_at_36%_28%,rgba(255,255,255,0.08),rgba(255,255,255,0.022)_72%)] shadow-[0_14px_40px_rgba(0,0,0,0.26)] backdrop-blur-sm"
              }`}
              style={{
                width: bubble.width,
                height: bubble.height,
                left: bubble.left,
                top: bubble.top,
                zIndex: bubble.accent ? 4 : 2,
              }}
            >
              {bubble.accent ? (
                <>
                  <div className="pointer-events-none absolute inset-[9%] rounded-full border border-white/[0.13]" />
                  <div className="pointer-events-none absolute inset-[20%] rounded-full border border-white/[0.06]" />
                </>
              ) : null}
              <div className={`font-semibold tracking-[-0.03em] text-white/88 ${bubble.accent ? "text-[1.1rem] sm:text-[1.2rem]" : "text-[0.88rem] sm:text-[0.95rem]"}`}>
                {bubble.label}
              </div>
              <div className={`leading-none tracking-[-0.07em] text-white ${bubble.accent ? "mt-1 text-[4rem] font-bold sm:text-[4.4rem]" : "mt-1 text-[2.45rem] font-bold sm:text-[2.7rem]"}`}>
                {bubble.share}
              </div>
              <div className={`tracking-[-0.01em] ${bubble.accent ? "mt-2 text-[0.92rem] text-white/55" : "mt-1.5 text-[0.78rem] text-white/40"}`}>
                {bubble.moments}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StartupArcZoom() {
  return (
    <div className="continuity-startup-arc-stage absolute inset-0 flex items-center justify-center px-6 sm:px-10">
      <div className="continuity-startup-arc-shell relative w-full max-w-[72rem] overflow-hidden rounded-[36px] border border-[#8cb7ff]/10 bg-[linear-gradient(158deg,rgba(11,17,32,0.97),rgba(7,10,20,0.96))] px-6 py-5 shadow-[0_44px_130px_rgba(0,0,0,0.42),0_0_0_1px_rgba(140,183,255,0.06),inset_0_1px_0_rgba(140,183,255,0.07)] backdrop-blur-xl sm:px-8 sm:py-6">
        {/* Top edge accent glow */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(140,183,255,0.35)_30%,rgba(180,210,255,0.5)_50%,rgba(140,183,255,0.35)_70%,transparent)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_15%_0%,rgba(108,145,225,0.14),transparent),radial-gradient(ellipse_40%_35%_at_88%_100%,rgba(100,75,55,0.10),transparent),radial-gradient(ellipse_30%_25%_at_50%_0%,rgba(140,183,255,0.06),transparent)]" />

        <div className="continuity-startup-kicker relative z-10 opacity-0">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
            <span className="h-1.5 w-1.5 rounded-full bg-[#8cb7ff]/70" />
            Start up
          </div>
          <div className="mt-3 text-[1.6rem] font-semibold tracking-[-0.05em] text-white sm:text-[1.85rem]">
            Continuity Arc
          </div>
        </div>

        {/* Lines near TOP of each row (~5.6%, 38.8%, 72.2% of total height).
            Row height = 9rem. Line at ~1.5rem from top → text zone = 7rem per row.
            Gap between rows is tight (~2rem), not the 12rem dead zone from midpoint lines. */}
        <div className="continuity-startup-map relative z-10 mt-5 h-[27rem] sm:h-[30rem]">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 1200 500"
            fill="none"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="arc-line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(140,183,255,0.40)" />
                <stop offset="35%" stopColor="rgba(180,210,255,0.72)" />
                <stop offset="65%" stopColor="rgba(180,210,255,0.72)" />
                <stop offset="100%" stopColor="rgba(140,183,255,0.40)" />
              </linearGradient>
            </defs>
            {/* Glow underlay */}
            <path
              d="M150 28 H1044 Q1092 28 1092 76 V146 Q1092 194 1044 194 H156 Q108 194 108 242 V313 Q108 361 156 361 H1050"
              stroke="rgba(140,183,255,0.16)"
              strokeWidth="7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Lines at y=28 (5.6%), y=194 (38.8%), y=361 (72.2%) */}
            <path
              className="continuity-startup-zigzag"
              d="M150 28 H1044 Q1092 28 1092 76 V146 Q1092 194 1044 194 H156 Q108 194 108 242 V313 Q108 361 156 361 H1050"
              pathLength="1"
              stroke="url(#arc-line-grad)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {startupArcStages.map((stage, index) => {
            const row = Math.floor(index / 4);
            const inRow = index % 4;
            const column = row % 2 === 0 ? inRow : 3 - inRow;
            const nodeLeft = ["12.5%", "37.5%", "62.5%", "87.5%"][column];
            // Nodes at line y positions: 5.6%, 38.8%, 72.2%
            const nodeTop = ["5.6%", "38.8%", "72.2%"][row];

            return (
              <div
                key={`${stage.title}-node`}
                className={`continuity-startup-node absolute -translate-x-1/2 -translate-y-1/2 rounded-full ${
                  stage.emphasis === "major"
                    ? "h-4 w-4 bg-[#8cb7ff] shadow-[0_0_0_3px_rgba(140,183,255,0.15),0_0_18px_rgba(140,183,255,0.55)]"
                    : "h-2.5 w-2.5 bg-[#8cb7ff]/80 shadow-[0_0_8px_rgba(140,183,255,0.42)]"
                }`}
                style={{ left: nodeLeft, top: nodeTop }}
              />
            );
          })}

          {/* Text BELOW each line. Line at ~1.5rem from row top → pt-[2rem] = 0.5rem gap.
              Text zone per row: 9rem - 2rem = 7rem. Ample for all content. */}
          <div className="relative z-10 grid h-full grid-cols-4 grid-rows-3 gap-x-4 sm:gap-x-6">
            {startupArcStages.map((stage, index) => {
              const row = Math.floor(index / 4);
              const inRow = index % 4;
              const column = row % 2 === 0 ? inRow : 3 - inRow;

              return (
                <div
                  key={stage.title}
                  className={`continuity-startup-stage continuity-startup-stage-${index + 1} relative flex items-start justify-center pt-8 sm:pt-9`}
                  style={{ gridColumn: column + 1, gridRow: row + 1 }}
                >
                  <div className="continuity-startup-card w-full max-w-full text-left">
                    <div className={`text-[8px] font-semibold uppercase tracking-[0.2em] ${
                      stage.emphasis === "major" ? "text-[#8cb7ff]/70" : "text-white/28"
                    }`}>
                      {stage.label}
                    </div>
                    <div
                      className={`mt-1 font-semibold tracking-[-0.04em] text-white ${
                        stage.emphasis === "major" ? "text-[1.05rem] sm:text-[1.15rem]" : "text-[0.88rem] sm:text-[0.92rem]"
                      }`}
                    >
                      {stage.title}
                    </div>
                    <p
                      className={`mt-1.5 tracking-[-0.015em] ${
                        stage.emphasis === "major"
                          ? "text-[0.8rem] leading-[1.5] text-white/68"
                          : "text-[0.72rem] leading-[1.4] text-white/44"
                      }`}
                    >
                      {stage.body}
                    </p>
                    <div className={`mt-2 text-[8px] font-semibold uppercase tracking-[0.2em] ${
                      stage.emphasis === "major" ? "text-[#8cb7ff]/80" : "text-[#8cb7ff]/50"
                    }`}>
                      {stage.meta}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Scene4Continuity() {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden px-8 sm:px-12 lg:px-16 xl:px-24">
      <div className="continuity-visual absolute inset-0 overflow-hidden">
        <div className="continuity-noise-field absolute inset-0">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(138,163,255,0.08),transparent_24%),radial-gradient(circle_at_82%_20%,rgba(138,163,255,0.08),transparent_28%),radial-gradient(circle_at_55%_78%,rgba(138,163,255,0.07),transparent_28%),linear-gradient(180deg,rgba(7,10,16,0.18),rgba(7,10,16,0.7))]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(2,6,23,0.1)_46%,rgba(2,6,23,0.56)_100%)]" />

          {continuityNoise.map((signal) => (
            <div
              key={signal.text}
              className={`continuity-noise-item pointer-events-none absolute left-1/2 top-1/2 whitespace-nowrap rounded-full border px-4 py-2 text-[clamp(0.85rem,1vw,1rem)] font-medium tracking-[-0.02em] ${
                signal.tone === "bright"
                  ? "border-[#c8d7ff]/16 bg-[#c8d7ff]/6 text-[#dce6ff]/80"
                  : "border-white/8 bg-white/[0.03] text-white/38"
              } ${
                signal.size === "lg"
                  ? "px-6 py-3 text-[clamp(1rem,1.2vw,1.3rem)]"
                  : signal.size === "sm"
                    ? "px-3 py-[0.45rem] text-[clamp(0.72rem,0.82vw,0.88rem)]"
                    : "px-4 py-2 text-[clamp(0.85rem,1vw,1rem)]"
              }`}
              data-x={signal.x}
              data-y={signal.y}
            >
              {signal.text}
            </div>
          ))}
        </div>

        <div className="continuity-core-wrap absolute inset-0 flex items-center justify-center">
          <div className="continuity-core-shell relative flex h-36 w-36 items-center justify-center rounded-full border border-[#8cb7ff]/35 bg-[radial-gradient(circle_at_center,rgba(140,183,255,0.28),rgba(100,145,230,0.14)_44%,rgba(7,11,21,0.88)_78%)] shadow-[0_0_60px_rgba(140,183,255,0.32),0_0_120px_rgba(140,183,255,0.12)]">
            <div className="continuity-core-ring absolute inset-[-18px] rounded-full border border-[#8cb7ff]/20" />
            <div className="continuity-core-ring absolute inset-[-34px] rounded-full border border-[#8cb7ff]/10" />
            <div className="continuity-core-label relative z-10 text-center">
              <div className="text-[1rem] font-semibold uppercase tracking-[0.38em] text-[#8cb7ff]/90">
                Sakhi
              </div>
            </div>
          </div>
        </div>

        <div className="continuity-output-stage absolute inset-0 flex flex-col items-center justify-center px-6 sm:px-10 lg:px-14">
          <OccupancyBoard />
          <StartupArcZoom />
        </div>
      </div>

      <div className="continuity-copy relative z-10 max-w-4xl opacity-0">
        <div className="continuity-line mb-6 text-xs tracking-[0.3em] text-white/40">
          CONTINUITY
        </div>

        <h1 className="continuity-line text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-white sm:text-6xl">
          Your life, connected across time.
        </h1>

        <div className="mt-10 space-y-4 text-lg leading-relaxed text-white/60">
          <p className="continuity-line">Noise becomes pattern.</p>
          <p className="continuity-line">Pattern becomes readable occupancy.</p>
          <p className="continuity-line">
            The system gathers scattered moments and returns which threads have actually occupied your life.
          </p>
          <p className="continuity-line">
            So it shows not just what is happening now, but what has been taking up space across time.
          </p>
          <p className="continuity-line pt-2 text-white/80">
            This is where scattered life becomes coherent.
          </p>
        </div>
      </div>
    </div>
  );
}

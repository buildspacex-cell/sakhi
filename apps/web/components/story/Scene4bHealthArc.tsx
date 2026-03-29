"use client";

// 6 months map to the same StartupArcZoom stage format.
// 2 rows × 3 cols snake: M1→M2→M3 (left→right), then M4→M5→M6 (right→left).
type HealthStage = {
  label: string;
  title: string;
  body: string;
  meta: string;
  emphasis?: "major" | "minor";
};

const healthStages: readonly HealthStage[] = [
  {
    label: "Where It Began",
    title: "First signal",
    body: "Skipped the gym. Told myself it was temporary — just a busy week.",
    meta: "Day 4",
    emphasis: "major",
  },
  {
    label: "Phase 2",
    title: "Late nights begin",
    body: "Staying up past midnight. Still feels manageable.",
    meta: "Day 11",
  },
  {
    label: "Phase 3",
    title: "Caffeine crutch",
    body: "Third coffee by noon. Energy borrowed from tomorrow.",
    meta: "Day 18",
  },
  {
    label: "Phase 4",
    title: "Sleep slips",
    body: "Seven hours became five. Body adjusted — or seemed to.",
    meta: "Day 29",
  },
  {
    label: "Phase 5",
    title: "First headache",
    body: "Headache at 3pm. Dismissed as screen fatigue.",
    meta: "Day 42",
  },
  {
    label: "Phase 6",
    title: "Energy dip",
    body: "Mid-day crashes. Calendar rearranged around low-energy windows.",
    meta: "Day 58",
  },
  {
    label: "Phase 7",
    title: "Focus fractures",
    body: "Couldn't hold the thread in a meeting. First real interference.",
    meta: "Day 71",
  },
  {
    label: "Phase 8",
    title: "Pre-stage drain",
    body: "Felt hollow before a major presentation. Something had shifted.",
    meta: "Day 88",
  },
  {
    label: "Phase 9",
    title: "Cross-arc link",
    body: "Career entries start mentioning energy. Sakhi detects the connection.",
    meta: "Day 104 · ↔ Career",
  },
  {
    label: "Phase 10",
    title: "Naming it",
    body: "'Am I burning out?' — first time the word appeared in the journal.",
    meta: "Day 122 · ↔ Career · Sleep",
  },
  {
    label: "Phase 11",
    title: "The real question",
    body: "'Is this pace sustainable?' The body had been asking for months.",
    meta: "Day 145 · ↔ Career · Sleep · Stress",
  },
  {
    label: "Where It Is Now",
    title: "Sakhi reflects",
    body: "Six months of signal. The thread is named, the pattern is clear, the moment for reflection has arrived.",
    meta: "164 days of signal",
    emphasis: "major",
  },
] as const;

// Health bubble occupancy: health dominates + 3 connected threads
type HealthBubble = {
  label: string;
  share: string;
  moments: string;
  width: string;
  height: string;
  left: string;
  top: string;
  accent?: boolean;
};

const healthBubbles: readonly HealthBubble[] = [
  {
    label: "Health",
    share: "41%",
    moments: "18 moments",
    width: "18rem",
    height: "18rem",
    left: "30%",
    top: "48%",
    accent: true,
  },
  {
    label: "Career",
    share: "26%",
    moments: "11 moments",
    width: "11rem",
    height: "11rem",
    left: "68%",
    top: "24%",
  },
  {
    label: "Sleep",
    share: "18%",
    moments: "8 moments",
    width: "9.5rem",
    height: "9.5rem",
    left: "72%",
    top: "58%",
  },
  {
    label: "Stress",
    share: "15%",
    moments: "6 moments",
    width: "8.5rem",
    height: "8.5rem",
    left: "56%",
    top: "78%",
  },
] as const;

function HealthOccupancyView() {
  return (
    <div className="health-occupancy-board relative mx-auto w-full max-w-[62rem] overflow-hidden rounded-[40px] border border-white/[0.09] bg-[linear-gradient(158deg,rgba(12,17,30,0.98),rgba(7,10,20,0.96))] shadow-[0_52px_160px_rgba(0,0,0,0.52),inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-2xl">
      {/* Ambient color bleeds — warm red for health */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_15%_10%,rgba(220,80,60,0.13),transparent),radial-gradient(ellipse_50%_45%_at_85%_88%,rgba(200,80,50,0.09),transparent),radial-gradient(ellipse_40%_35%_at_80%_8%,rgba(230,100,70,0.07),transparent)]" />

      <div className="health-occupancy-shell relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between gap-5 border-b border-white/[0.06] px-7 pb-5 pt-6 sm:px-9 sm:pt-7">
          <div className="health-occupancy-copy">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
              <span className="h-1.5 w-1.5 rounded-full bg-[#ff8070]/70" />
              Vidhya · Health Thread
            </div>
            <div className="mt-3 text-[1.85rem] font-semibold tracking-[-0.055em] text-white sm:text-[2rem]">
              Signal Occupancy
            </div>
            <p className="mt-1.5 max-w-[30rem] text-[0.9rem] leading-[1.65] tracking-[-0.015em] text-white/44">
              By month 6, health occupies the largest share — threading into career, sleep, and stress.
            </p>
          </div>

          <div className="shrink-0 rounded-2xl border border-white/[0.09] bg-white/[0.03] px-4 py-3 text-right backdrop-blur-sm">
            <div className="text-[9px] font-semibold uppercase tracking-[0.26em] text-white/30">Connected</div>
            <div className="mt-1.5 text-[1.05rem] font-semibold tracking-[-0.04em] text-white/82">3 threads</div>
          </div>
        </div>

        {/* Bubble cloud */}
        <div className="health-bubble-cloud relative h-[26rem] overflow-visible px-2 sm:h-[28rem]">
          {/* Soft inner glow */}
          <div className="pointer-events-none absolute left-[22%] top-0 h-48 w-48 -translate-x-1/2 rounded-full bg-[#ff6050]/7 blur-3xl" />
          <div className="pointer-events-none absolute right-[18%] top-[30%] h-40 w-40 rounded-full bg-[#ff8060]/5 blur-3xl" />
          <div className="pointer-events-none absolute bottom-0 left-[10%] h-36 w-36 rounded-full bg-[#ff5040]/5 blur-3xl" />

          <svg
            className="pointer-events-none absolute inset-0 h-full w-full"
            viewBox="0 0 1000 580"
            fill="none"
            preserveAspectRatio="none"
          >
            {/* Arcs connecting health bubble to satellites */}
            <path d="M310 255C400 190 530 185 630 210" stroke="rgba(255,140,110,0.14)" strokeWidth="1.2" strokeLinecap="round" />
            <path d="M324 370C430 415 560 415 650 390" stroke="rgba(255,140,110,0.09)" strokeWidth="1.2" strokeLinecap="round" />
            <path d="M710 185C758 238 778 312 770 390" stroke="rgba(255,140,110,0.08)" strokeWidth="1" strokeDasharray="4 12" strokeLinecap="round" />
          </svg>

          {healthBubbles.map((bubble) => (
            <div
              key={bubble.label}
              className={`health-occupancy-bubble ${bubble.accent ? "health-main-bubble" : ""} absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full text-center ${
                bubble.accent
                  ? "border border-[#ff9080]/45 bg-[radial-gradient(circle_at_36%_28%,rgba(255,180,160,0.22),rgba(220,100,80,0.28)_48%,rgba(100,35,30,0.40)_100%)] shadow-[0_0_80px_rgba(255,100,80,0.20),0_24px_64px_rgba(0,0,0,0.40)]"
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
                  <div className="pointer-events-none absolute inset-[9%] rounded-full border border-[#ff9070]/[0.18]" />
                  <div className="pointer-events-none absolute inset-[20%] rounded-full border border-[#ff9070]/[0.09]" />
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

function HealthArcZoom() {
  return (
    <div className="health-arc-stage absolute inset-0 flex items-center justify-center px-6 sm:px-10">
      <div className="health-arc-shell relative w-full max-w-[72rem] overflow-hidden rounded-[36px] border border-[#ff8070]/10 bg-[linear-gradient(158deg,rgba(11,17,32,0.97),rgba(7,10,20,0.96))] px-6 py-5 shadow-[0_44px_130px_rgba(0,0,0,0.42),0_0_0_1px_rgba(255,128,112,0.06),inset_0_1px_0_rgba(255,128,112,0.07)] backdrop-blur-xl sm:px-8 sm:py-6">
        {/* Top edge accent glow — warm red */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-[linear-gradient(90deg,transparent,rgba(255,110,90,0.35)_30%,rgba(255,160,130,0.5)_50%,rgba(255,110,90,0.35)_70%,transparent)]" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_45%_at_15%_0%,rgba(220,80,60,0.12),transparent),radial-gradient(ellipse_40%_35%_at_88%_100%,rgba(180,60,50,0.08),transparent),radial-gradient(ellipse_30%_25%_at_50%_0%,rgba(255,100,80,0.05),transparent)]" />

        <div className="health-arc-kicker relative z-10 opacity-0">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[9px] font-semibold uppercase tracking-[0.28em] text-white/40">
            <span className="h-1.5 w-1.5 rounded-full bg-[#ff8070]/70" />
            Health
          </div>
          <div className="mt-3 text-[1.6rem] font-semibold tracking-[-0.05em] text-white sm:text-[1.85rem]">
            The Quiet Toll
          </div>
        </div>

        {/* 3-row × 4-col snake — identical layout to startup arc.
            SVG viewBox 1200 × 500.
            Lines at y=28 (5.6%), y=194 (38.8%), y=361 (72.2%). */}
        <div className="health-arc-map relative z-10 mt-5 h-[27rem] sm:h-[30rem]">
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 1200 500"
            fill="none"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="health-line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="rgba(255,110,90,0.38)" />
                <stop offset="35%" stopColor="rgba(255,160,130,0.70)" />
                <stop offset="65%" stopColor="rgba(255,160,130,0.70)" />
                <stop offset="100%" stopColor="rgba(255,110,90,0.38)" />
              </linearGradient>
            </defs>
            {/* Glow underlay */}
            <path
              d="M150 28 H1044 Q1092 28 1092 76 V146 Q1092 194 1044 194 H156 Q108 194 108 242 V313 Q108 361 156 361 H1050"
              stroke="rgba(255,110,90,0.14)"
              strokeWidth="7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Main path */}
            <path
              className="health-arc-zigzag"
              d="M150 28 H1044 Q1092 28 1092 76 V146 Q1092 194 1044 194 H156 Q108 194 108 242 V313 Q108 361 156 361 H1050"
              pathLength="1"
              stroke="url(#health-line-grad)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {/* Nodes — 12 stages, 4 per row, snake direction */}
          {healthStages.map((stage, index) => {
            const row = Math.floor(index / 4);
            const inRow = index % 4;
            const column = row % 2 === 0 ? inRow : 3 - inRow;
            const nodeLeft = ["12.5%", "37.5%", "62.5%", "87.5%"][column];
            const nodeTop = ["5.6%", "38.8%", "72.2%"][row];

            return (
              <div
                key={`${stage.title}-node`}
                className={`health-arc-node absolute -translate-x-1/2 -translate-y-1/2 rounded-full ${
                  stage.emphasis === "major"
                    ? "h-4 w-4 bg-[#ff8070] shadow-[0_0_0_3px_rgba(255,128,112,0.15),0_0_18px_rgba(255,128,112,0.55)]"
                    : "h-2.5 w-2.5 bg-[#ff8070]/80 shadow-[0_0_8px_rgba(255,128,112,0.42)]"
                }`}
                style={{ left: nodeLeft, top: nodeTop }}
              />
            );
          })}

          {/* Text cards — same pt-8 sm:pt-9, all below the line */}
          <div className="relative z-10 grid h-full grid-cols-4 grid-rows-3 gap-x-4 sm:gap-x-6">
            {healthStages.map((stage, index) => {
              const row = Math.floor(index / 4);
              const inRow = index % 4;
              const column = row % 2 === 0 ? inRow : 3 - inRow;

              return (
                <div
                  key={stage.title}
                  className={`health-arc-stage-cell health-arc-stage-cell-${index + 1} relative flex items-start justify-center pt-8 sm:pt-9`}
                  style={{ gridColumn: column + 1, gridRow: row + 1 }}
                >
                  <div className="health-arc-card w-full max-w-full text-left">
                    <div className={`text-[8px] font-semibold uppercase tracking-[0.2em] ${
                      stage.emphasis === "major" ? "text-[#ff8070]/70" : "text-white/28"
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
                      stage.emphasis === "major" ? "text-[#ff8070]/80" : "text-[#ff8070]/50"
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

export default function Scene4bHealthArc() {
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden px-8 sm:px-12 lg:px-16 xl:px-24">
      {/* Ambient warm glow */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_50%_40%_at_30%_55%,rgba(255,70,50,0.04),transparent)]" />

      <div className="health-visual absolute inset-0 overflow-hidden">
        <div className="health-output-stage absolute inset-x-0 bottom-6 px-6 sm:bottom-8 sm:px-10 lg:bottom-10">
          <HealthOccupancyView />
          <HealthArcZoom />
        </div>
      </div>
    </div>
  );
}

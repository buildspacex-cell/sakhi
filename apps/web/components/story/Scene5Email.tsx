"use client";

import Image from "next/image";

type ProductPanel = {
  key: string;
  label: string;
  headline: string;
  lead: string;
  details: string[];
  src: string;
  alt: string;
  caption: string;
  privacy?: boolean;
};

const productPanels: ProductPanel[] = [
  {
    key: "conversation",
    label: "Conversation",
    headline: "Start talking. Sakhi does the rest.",
    lead: "It keeps the thread.",
    details: ["It builds over time.", "It evolves with you."],
    src: "/story/chat.png",
    alt: "Sakhi chat screen",
    caption: "Start anywhere. Sakhi keeps the thread.",
  },
  {
    key: "reflection",
    label: "Life Occupancy",
    headline: "Your life becomes visible.",
    lead: "Across time and topics, everything connects.",
    details: [
      "What you have lived begins to form patterns.",
      "Not just moments, but something you can understand.",
    ],
    src: "/story/reflection.png",
    alt: "Sakhi reflection screen",
    caption: "Threads emerge from what you have actually lived.",
  },
  {
    key: "moments",
    label: "Continuity",
    headline: "Your story starts to take shape.",
    lead: "Each thread becomes something you can return to, and build on.",
    details: [
      "What you have lived stays connected, forming a timeline you can move through.",
      "And over time, those moments begin to form your story.",
    ],
    src: "/story/continuity.PNG",
    alt: "Sakhi continuity screen",
    caption: "Continuity becomes visible across what you have lived.",
  },
  {
    key: "privacy",
    label: "Privacy",
    headline: "What you share stays yours.",
    lead: "Private by design. Yours to control.",
    details: [
      "Your conversations are encrypted end-to-end.",
      "You decide what Sakhi remembers.",
    ],
    src: "/story/vidz-space.png",
    alt: "Sakhi privacy and account screen",
    caption: "Private by default.",
    privacy: true,
  },
];

export default function Scene5Email() {
  return (
    <div className="relative h-full overflow-hidden px-8 pb-36 pt-8 sm:px-12 sm:pb-40 sm:pt-10 lg:px-16 lg:pb-44 xl:px-24 xl:pb-48">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_22%,rgba(139,160,255,0.18),transparent_24%),radial-gradient(circle_at_22%_68%,rgba(112,136,255,0.10),transparent_28%),radial-gradient(circle_at_78%_72%,rgba(157,177,255,0.10),transparent_28%)]" />

      <div className="product-intro absolute inset-0 z-20 flex items-center justify-center px-8 text-center opacity-0 sm:px-12 lg:px-16 xl:px-24">
        <div className="max-w-3xl">
          <p className="text-balance text-[2.8rem] font-semibold leading-[0.98] tracking-[-0.06em] text-white sm:text-[4rem] lg:text-[5rem]">
            First expression of Sakhi.
          </p>
        </div>
      </div>

      <div className="product-stage absolute inset-0">
        {productPanels.map((panel, index) => (
          <div
            key={panel.key}
            className={`product-panel product-panel-${index + 1} absolute inset-0 flex items-center justify-center px-8 pb-28 pt-14 opacity-0 sm:px-12 sm:pb-32 sm:pt-16 lg:px-16 lg:pb-36 lg:pt-[4.5rem] xl:px-24 xl:pb-40 xl:pt-20`}
          >
            <div
              className="relative flex w-full max-w-[1280px] items-center justify-between gap-[clamp(32px,4vw,64px)] overflow-hidden rounded-[42px] border border-[rgba(189,206,225,0.14)] bg-[linear-gradient(155deg,rgba(16,23,39,0.95),rgba(7,11,21,0.84))] px-[clamp(40px,5vw,72px)] py-[clamp(36px,4vw,56px)] shadow-[0_48px_140px_rgba(0,0,0,0.48)] backdrop-blur-[24px]"
              style={{ minHeight: "min(76vh, 780px)" }}
            >
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_18%,rgba(84,122,142,0.18),transparent_32%),radial-gradient(circle_at_86%_82%,rgba(153,112,58,0.12),transparent_25%)]" />

              <div className={`product-panel-copy product-panel-copy-${index + 1} relative z-10 max-w-[560px] flex-1`}>
                <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.28em] text-[#b9c9e8] sm:text-[11px]">
                  <span className="h-3 w-3 rounded-full bg-[#dce7f8] shadow-[0_0_18px_rgba(220,231,248,0.35)]" />
                  {panel.label}
                </div>

                <h2 className="mt-8 max-w-[12.4ch] text-balance text-[clamp(44px,4.9vw,58px)] font-extrabold leading-[0.96] tracking-[-0.055em] text-white">
                  {panel.headline}
                </h2>

                <p className="mt-8 max-w-[18ch] text-balance text-[clamp(22px,2.25vw,26px)] font-semibold leading-[1.5] tracking-[-0.03em] text-slate-100">
                  {panel.lead}
                </p>

                <div className="mt-8 space-y-6 text-[clamp(18px,1.8vw,21px)] leading-[1.62] tracking-[-0.02em] text-slate-300">
                  {panel.details.map((detail) => (
                    <p key={detail} className="max-w-[30ch] text-balance">
                      {detail}
                    </p>
                  ))}
                </div>

                {panel.privacy ? (
                  <div className="mt-8 flex items-center gap-6">
                    <div className="flex h-24 w-24 items-center justify-center rounded-full border border-white/10 bg-[radial-gradient(circle_at_50%_35%,rgba(210,224,255,0.16),rgba(210,224,255,0.04)_54%,transparent_72%)] shadow-[0_18px_54px_rgba(0,0,0,0.28)]">
                      <div className="relative h-12 w-10">
                        <div className="absolute left-1/2 top-0 h-6 w-7 -translate-x-1/2 rounded-t-full border-[4px] border-b-0 border-slate-200/90" />
                        <div className="absolute bottom-0 left-1/2 h-8 w-10 -translate-x-1/2 rounded-[12px] bg-[linear-gradient(180deg,#e8eefb,#cfd8ea)] shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
                          <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-slate-700" />
                          <div className="absolute left-1/2 top-[58%] h-3.5 w-[2px] -translate-x-1/2 rounded-full bg-slate-700" />
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>

              <div className={`product-panel-phone product-panel-phone-${index + 1} relative z-10 flex flex-none translate-y-3 flex-col items-center self-center`}>
                <div
                  className="relative z-[1] flex flex-col items-center rounded-[44px] border border-[rgba(189,206,225,0.12)] bg-[linear-gradient(180deg,rgba(18,28,45,0.78),rgba(8,13,24,0.54))] shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_60px_rgba(0,0,0,0.28)]"
                  style={{
                    padding:
                      "clamp(14px, 1.5vw, 18px) clamp(14px, 1.5vw, 18px) clamp(18px, 1.8vw, 22px)",
                  }}
                >
                  <div className="mb-[14px] h-[5px] w-[92px] rounded-full bg-white/10" />
                  <div
                    className="relative overflow-hidden rounded-[36px] border border-[rgba(203,213,225,0.16)] bg-[#040914] shadow-[0_36px_90px_rgba(0,0,0,0.55)]"
                    style={{
                      width: "min(clamp(295px, 28vw, 400px), calc((100vh - 290px) * 0.5625))",
                    }}
                  >
                    <Image
                      src={panel.src}
                      alt={panel.alt}
                      width={720}
                      height={1280}
                      className="block h-auto w-full"
                    />
                  </div>
                </div>
                <p className={`product-panel-caption product-panel-caption-${index + 1} mt-3 max-w-[270px] text-center text-[13px] leading-[1.5] tracking-[0.01em] text-slate-500`}>
                  {panel.caption}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}

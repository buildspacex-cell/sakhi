"use client";

import Image from "next/image";
import { FadeIn } from "@/components/pitch/FadeIn";

const productPanels = [
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
    label: "Reflection",
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
    lead: "Your conversations are yours, not ours.",
    details: [
      "End-to-end encrypted.",
      "No one reads your conversations.",
      "Not even Sakhi.",
    ],
    src: "/story/vidz-space.png",
    alt: "Sakhi privacy and account screen",
    caption: "Private by default.",
    privacy: true,
  },
];

export function PitchProduct() {
  return (
    <section id="product" className="border-t border-white/[0.06] bg-[#020617] px-8 py-24 scroll-mt-16 sm:px-12 lg:px-16 xl:px-24">
      <FadeIn>
        <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8ab0ff]/80 mb-10">
          First Expression Of Sakhi
        </p>
      </FadeIn>

      <FadeIn delay={100}>
        <h2
          className="max-w-[13ch] text-balance text-white leading-[0.98] -tracking-[0.055em] font-semibold"
          style={{ fontSize: "clamp(2.8rem, 5vw, 4.8rem)" }}
        >
          The product starts where life actually happens.
        </h2>
      </FadeIn>

      <FadeIn delay={180}>
        <p className="mt-6 max-w-3xl text-[1.08rem] leading-[1.75] tracking-[-0.02em] text-white/56 sm:text-[1.16rem]">
          Conversation, reflection, moments, and privacy form the first expression of Sakhi.
        </p>
      </FadeIn>

      <div className="mt-14 flex flex-col gap-10">
        {productPanels.map((panel, index) => (
          <FadeIn key={panel.key} delay={index * 80}>
            <div className="relative flex w-full items-center justify-between gap-[clamp(28px,4vw,64px)] overflow-hidden rounded-[42px] border border-[rgba(189,206,225,0.14)] bg-[linear-gradient(155deg,rgba(16,23,39,0.95),rgba(7,11,21,0.84))] px-[clamp(32px,5vw,72px)] py-[clamp(32px,4vw,56px)] shadow-[0_48px_140px_rgba(0,0,0,0.48)] backdrop-blur-[24px]"
              style={{ minHeight: "min(72vh, 700px)" }}
            >
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_14%_18%,rgba(84,122,142,0.18),transparent_32%),radial-gradient(circle_at_86%_82%,rgba(153,112,58,0.12),transparent_25%)]" />

              {/* Copy */}
              <div className="relative z-10 max-w-[560px] flex-1">
                <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.05] px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.28em] text-[#b9c9e8] sm:text-[11px]">
                  <span className="h-3 w-3 rounded-full bg-[#dce7f8] shadow-[0_0_18px_rgba(220,231,248,0.35)]" />
                  {panel.label}
                </div>

                <h2 className="mt-8 max-w-[12.4ch] text-balance text-[clamp(36px,4.2vw,58px)] font-extrabold leading-[0.96] tracking-[-0.055em] text-white">
                  {panel.headline}
                </h2>

                <p className="mt-8 max-w-[18ch] text-balance text-[clamp(18px,1.9vw,26px)] font-semibold leading-[1.5] tracking-[-0.03em] text-slate-100">
                  {panel.lead}
                </p>

                <div className="mt-6 space-y-4 text-[clamp(15px,1.5vw,19px)] leading-[1.62] tracking-[-0.02em] text-slate-300">
                  {panel.details.map((detail) => (
                    <p key={detail} className="max-w-[30ch] text-balance">
                      {detail}
                    </p>
                  ))}
                </div>

                {panel.privacy ? (
                  <div className="mt-8 flex items-center gap-6">
                    <div className="flex h-20 w-20 items-center justify-center rounded-full border border-white/10 bg-[radial-gradient(circle_at_50%_35%,rgba(210,224,255,0.16),rgba(210,224,255,0.04)_54%,transparent_72%)] shadow-[0_18px_54px_rgba(0,0,0,0.28)]">
                      <div className="relative h-10 w-9">
                        <div className="absolute left-1/2 top-0 h-5 w-6 -translate-x-1/2 rounded-t-full border-[3px] border-b-0 border-slate-200/90" />
                        <div className="absolute bottom-0 left-1/2 h-7 w-9 -translate-x-1/2 rounded-[10px] bg-[linear-gradient(180deg,#e8eefb,#cfd8ea)] shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
                          <div className="absolute left-1/2 top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-slate-700" />
                          <div className="absolute left-1/2 top-[58%] h-3 w-[2px] -translate-x-1/2 rounded-full bg-slate-700" />
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* Phone mockup */}
              <div className="relative z-10 flex flex-none translate-y-3 flex-col items-center self-center">
                <div
                  className="relative z-[1] flex flex-col items-center rounded-[44px] border border-[rgba(189,206,225,0.12)] bg-[linear-gradient(180deg,rgba(18,28,45,0.78),rgba(8,13,24,0.54))] shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_20px_60px_rgba(0,0,0,0.28)]"
                  style={{ padding: "clamp(12px,1.5vw,18px) clamp(12px,1.5vw,18px) clamp(16px,1.8vw,22px)" }}
                >
                  <div className="mb-[14px] h-[5px] w-[92px] rounded-full bg-white/10" />
                  <div
                    className="relative overflow-hidden rounded-[36px] border border-[rgba(203,213,225,0.16)] bg-[#040914] shadow-[0_36px_90px_rgba(0,0,0,0.55)]"
                    style={{ width: "min(clamp(240px,24vw,380px), calc((100vh - 290px) * 0.5625))" }}
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
                <p className="mt-3 max-w-[270px] text-center text-[13px] leading-[1.5] tracking-[0.01em] text-slate-500">
                  {panel.caption}
                </p>
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}

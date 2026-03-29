"use client";

import { useState } from "react";

import { AnimatePresence, motion } from "framer-motion";

type DetailGroup = {
  title: string;
  items: readonly string[];
};

type ExpandableSectionProps = {
  system: string;
  stage?: string;
  title: string;
  summary: string;
  existsNow: readonly string[];
  visionHolds: readonly string[];
  featureTitle?: string;
  featureItems?: readonly string[];
  details: readonly DetailGroup[];
  visionOnly?: boolean;
};

export default function ExpandableSection({
  system,
  stage,
  title,
  summary,
  existsNow,
  visionHolds,
  featureTitle,
  featureItems = [],
  details,
  visionOnly = false,
}: ExpandableSectionProps) {
  const [open, setOpen] = useState(false);
  const [futureOpen, setFutureOpen] = useState(false);
  const [technicalOpen, setTechnicalOpen] = useState(false);

  return (
    <div className="rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,22,32,0.92),rgba(10,13,19,0.96))] p-6 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-400">
            {system}
          </div>
          {stage ? (
            <div className="mt-2 text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c4d2ff]">
              {stage}
            </div>
          ) : null}
        </div>
      </div>

      <h3 className="mt-4 max-w-[16ch] text-[1.85rem] font-semibold leading-[1.04] tracking-[-0.045em] text-white">
        {title}
      </h3>
      <p className="mt-4 max-w-[34ch] text-sm leading-7 text-slate-300">
        {summary}
      </p>

      <button
        type="button"
        onClick={() => {
          setOpen((value) => {
            const next = !value;
            if (!next) {
              setFutureOpen(false);
              setTechnicalOpen(false);
            }
            return next;
          });
        }}
        className="mt-5 inline-flex items-center gap-2 text-sm font-medium tracking-[-0.01em] text-[#c8d6ff] transition-opacity hover:opacity-80"
      >
        {open ? "Hide layer" : "Explore this layer"}
        <span aria-hidden="true">{open ? "↑" : "→"}</span>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            key="details"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="mt-6 space-y-6 border-t border-white/8 pt-6">
              <div className="rounded-[22px] border border-white/8 bg-white/[0.03] p-4">
                <div
                  className={`text-[10px] font-semibold uppercase tracking-[0.26em] ${
                    visionOnly ? "text-[#c4d2ff]" : "text-slate-400"
                  }`}
                >
                  {visionOnly ? "Vision direction" : "Exists now"}
                </div>
                <div className="mt-3 space-y-2">
                  {(visionOnly ? visionHolds : existsNow).map((item) => (
                    <div key={item} className="text-sm leading-6 text-slate-200">
                      {item}
                    </div>
                  ))}
                </div>
              </div>

              {featureItems.length ? (
                <div className="rounded-[22px] border border-white/8 bg-white/[0.02] p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-400">
                    {featureTitle ?? "Feature layer"}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {featureItems.map((item) => (
                      <div
                        key={item}
                        className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[0.8rem] leading-none text-slate-200"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {visionOnly ? (
                <>
                  <button
                    type="button"
                    onClick={() => setTechnicalOpen((value) => !value)}
                    className="inline-flex items-center gap-2 text-sm font-medium tracking-[-0.01em] text-[#c8d6ff] transition-opacity hover:opacity-80"
                  >
                    {technicalOpen ? "Hide technical foundations" : "See technical foundations"}
                    <span aria-hidden="true">{technicalOpen ? "↑" : "→"}</span>
                  </button>

                  <AnimatePresence initial={false}>
                    {technicalOpen ? (
                      <motion.div
                        key="technical-vision"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-5 border-t border-white/8 pt-6">
                          {details.map((group) => (
                            <div key={group.title}>
                              <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c4d2ff]">
                                {group.title}
                              </div>
                              <div className="mt-3 flex flex-wrap gap-2">
                                {group.items.map((item) => (
                                  <div
                                    key={item}
                                    className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[0.8rem] leading-none text-slate-200"
                                  >
                                    {item}
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setFutureOpen((value) => {
                        const next = !value;
                        if (!next) {
                          setTechnicalOpen(false);
                        }
                        return next;
                      });
                    }}
                    className="inline-flex items-center gap-2 text-sm font-medium tracking-[-0.01em] text-[#c8d6ff] transition-opacity hover:opacity-80"
                  >
                    {futureOpen ? "Hide what this becomes" : "See what this becomes"}
                    <span aria-hidden="true">{futureOpen ? "↑" : "→"}</span>
                  </button>

                  <AnimatePresence initial={false}>
                    {futureOpen ? (
                      <motion.div
                        key="future"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                        className="overflow-hidden"
                      >
                        <div className="space-y-6 border-t border-white/8 pt-6">
                          <div className="rounded-[22px] border border-[#90a8ff]/12 bg-[#90a8ff]/[0.04] p-4">
                            <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c4d2ff]">
                              What this becomes
                            </div>
                            <div className="mt-3 space-y-2">
                              {visionHolds.map((item) => (
                                <div key={item} className="text-sm leading-6 text-slate-200">
                                  {item}
                                </div>
                              ))}
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => setTechnicalOpen((value) => !value)}
                            className="inline-flex items-center gap-2 text-sm font-medium tracking-[-0.01em] text-[#c8d6ff] transition-opacity hover:opacity-80"
                          >
                            {technicalOpen ? "Hide technical foundations" : "See technical foundations"}
                            <span aria-hidden="true">{technicalOpen ? "↑" : "→"}</span>
                          </button>

                          <AnimatePresence initial={false}>
                            {technicalOpen ? (
                              <motion.div
                                key="technical"
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.3, ease: "easeOut" }}
                                className="overflow-hidden"
                              >
                                <div className="space-y-5 border-t border-white/8 pt-6">
                                  {details.map((group) => (
                                    <div key={group.title}>
                                      <div className="text-[10px] font-semibold uppercase tracking-[0.26em] text-[#c4d2ff]">
                                        {group.title}
                                      </div>
                                      <div className="mt-3 flex flex-wrap gap-2">
                                        {group.items.map((item) => (
                                          <div
                                            key={item}
                                            className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[0.8rem] leading-none text-slate-200"
                                          >
                                            {item}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </motion.div>
                            ) : null}
                          </AnimatePresence>
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </>
              )}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

type StorySection = {
  id: string;
  label: string;
};

type ScrollProgressProps = {
  containerId: string;
};

export default function ScrollProgress({ containerId }: ScrollProgressProps) {
  const [sections, setSections] = useState<StorySection[]>([]);
  const [activeId, setActiveId] = useState("");

  useEffect(() => {
    const container = document.getElementById(containerId);
    if (!container) {
      return;
    }

    const storySections = Array.from(
      container.querySelectorAll<HTMLElement>("[data-story-section='true']"),
    )
      .map((section, index) => {
        const fallbackId = `story-section-${index + 1}`;
        if (!section.id) {
          section.id = fallbackId;
        }

        return {
          id: section.id,
          label: section.dataset.storyLabel || `Section ${index + 1}`,
        };
      })
      .filter((section) => section.label);

    setSections(storySections);
    setActiveId(storySections[0]?.id || "");

    const ratios = new Map<string, number>();

    const updateActiveSection = () => {
      const nextActiveId =
        Array.from(ratios.entries())
          .sort((left, right) => right[1] - left[1])
          .find(([, ratio]) => ratio > 0)?.[0] || storySections[0]?.id;

      if (nextActiveId) {
        setActiveId(nextActiveId);
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          ratios.set((entry.target as HTMLElement).id, entry.intersectionRatio);
        });
        updateActiveSection();
      },
      {
        root: container,
        threshold: [0.2, 0.45, 0.7],
      },
    );

    storySections.forEach(({ id }) => {
      const section = document.getElementById(id);
      if (section) {
        observer.observe(section);
      }
    });

    return () => {
      observer.disconnect();
    };
  }, [containerId]);

  if (sections.length === 0) {
    return null;
  }

  return (
    <nav
      aria-label="Story progress"
      className="pointer-events-none fixed right-4 top-1/2 z-30 hidden -translate-y-1/2 md:flex"
    >
      <div className="pointer-events-auto rounded-full border border-white/10 bg-[#10141c]/80 px-3 py-3 shadow-panel backdrop-blur-xl">
        <div className="flex flex-col gap-2">
          {sections.map((section) => {
            const isActive = section.id === activeId;

            return (
              <button
                key={section.id}
                type="button"
                onClick={() => {
                  document.getElementById(section.id)?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
                }}
                className={`group flex items-center gap-3 rounded-full px-2 py-2 text-left transition ${
                  isActive ? "bg-white/6" : "bg-transparent"
                }`}
              >
                <span
                  className={`block h-2.5 w-2.5 rounded-full border transition ${
                    isActive
                      ? "border-[#9fb9ff] bg-[#9fb9ff] shadow-[0_0_16px_rgba(159,185,255,0.6)]"
                      : "border-white/25 bg-transparent"
                  }`}
                />
                <span
                  className={`text-[10px] font-semibold uppercase tracking-[0.28em] transition ${
                    isActive ? "text-white" : "text-slate-500 group-hover:text-slate-300"
                  }`}
                >
                  {section.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

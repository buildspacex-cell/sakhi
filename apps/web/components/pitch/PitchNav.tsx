"use client";

import { useEffect, useState } from "react";

const sections = [
  { id: "hero", label: "Story" },
  { id: "problem", label: "Problem" },
  { id: "solution", label: "Sakhi" },
  { id: "continuity", label: "Continuity" },
  { id: "product", label: "Product" },
  { id: "vision", label: "Vision" },
  { id: "founders", label: "Founders" },
  { id: "ask", label: "Ask" },
];

export function PitchNav() {
  const [activeId, setActiveId] = useState<string>("hero");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    const observers: IntersectionObserver[] = [];

    const visibilityMap: Record<string, number> = {};

    sections.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (!el) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            visibilityMap[id] = entry.intersectionRatio;
          });

          let maxRatio = 0;
          let mostVisible = activeId;
          for (const [sectionId, ratio] of Object.entries(visibilityMap)) {
            if (ratio > maxRatio) {
              maxRatio = ratio;
              mostVisible = sectionId;
            }
          }
          setActiveId(mostVisible);
        },
        {
          threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
          rootMargin: "-10% 0px -10% 0px",
        }
      );

      observer.observe(el);
      observers.push(observer);
    });

    return () => {
      observers.forEach((o) => o.disconnect());
    };
  }, [activeId]);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <nav className="fixed right-4 sm:right-6 top-1/2 z-50 hidden -translate-y-1/2 md:flex flex-col gap-3">
      {sections.map(({ id, label }) => {
        const isActive = activeId === id;
        const isHovered = hoveredId === id;

        return (
          <div
            key={id}
            className="relative flex items-center justify-end"
            onMouseEnter={() => setHoveredId(id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            {isHovered && (
              <span className="absolute right-6 mr-2 whitespace-nowrap rounded-lg border border-white/10 bg-[#020617]/90 px-2.5 py-1 text-[11px] font-medium text-white/80 backdrop-blur-sm">
                {label}
              </span>
            )}
            <button
              onClick={() => scrollTo(id)}
              aria-label={`Go to ${label}`}
              className={`h-2.5 w-2.5 rounded-full transition-all duration-300 ${
                isActive
                  ? "bg-white opacity-100 scale-125"
                  : "bg-white opacity-25 hover:opacity-50"
              }`}
            />
          </div>
        );
      })}
    </nav>
  );
}

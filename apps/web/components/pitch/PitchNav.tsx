"use client";

import { useCallback, useEffect, useState } from "react";

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
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      return;
    }

    document.exitFullscreen().catch(() => {});
  }, []);

  return (
    <nav className="fixed right-4 sm:right-6 top-1/2 z-50 hidden -translate-y-1/2 md:flex flex-col gap-3">
      <button
        type="button"
        onClick={toggleFullscreen}
        aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
        className="mb-2 flex h-11 w-11 items-center justify-center rounded-full border border-white/12 bg-[#020617]/80 text-white/78 shadow-[0_18px_40px_rgba(0,0,0,0.28)] backdrop-blur-md transition hover:border-white/20 hover:bg-[#08111f]/92 hover:text-white"
      >
        {isFullscreen ? (
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-4 w-4 fill-none stroke-current"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
          </svg>
        ) : (
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="h-4 w-4 fill-none stroke-current"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
          </svg>
        )}
      </button>
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

"use client";

import type { ScenarioConfig } from "@/app/demo/simulation/types";
import { govPalette } from "../theme";

interface TimelineNavProps {
  scenarios: ScenarioConfig[];
  currentIndex: number;
  completedIndices: Set<number>;
  onSelect: (index: number) => void;
  showEpilogue: boolean;
  onEpilogue: () => void;
}

export default function TimelineNav({
  scenarios,
  currentIndex,
  completedIndices,
  onSelect,
  showEpilogue,
  onEpilogue,
}: TimelineNavProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 0,
        padding: "16px 0",
        width: "100%",
        overflowX: "auto",
      }}
    >
      {scenarios.map((scenario, i) => {
        const isActive = i === currentIndex && !showEpilogue;
        const isCompleted = completedIndices.has(i);
        const isAccessible = i <= Math.max(...Array.from(completedIndices), 0) + 1;

        return (
          <div key={scenario.id} style={{ display: "flex", alignItems: "center" }}>
            <button
              onClick={() => isAccessible && onSelect(i)}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
                background: "none",
                border: "none",
                cursor: isAccessible ? "pointer" : "default",
                opacity: isAccessible ? 1 : 0.4,
                padding: "4px 8px",
                transition: "opacity 0.3s",
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 16,
                  background: isActive
                    ? govPalette.accent
                    : isCompleted
                    ? `${govPalette.allow}20`
                    : govPalette.cardAlt,
                  border: `2px solid ${
                    isActive ? govPalette.accent : isCompleted ? govPalette.allow : govPalette.border
                  }`,
                  color: isActive ? "#fff" : govPalette.text,
                  transition: "all 0.3s",
                }}
              >
                {isCompleted && !isActive ? "\u2713" : scenario.icon}
              </div>
              <div style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: isActive ? govPalette.text : govPalette.dim,
                    whiteSpace: "nowrap",
                  }}
                >
                  {scenario.time}
                </div>
                <div
                  style={{
                    fontSize: 9,
                    color: isActive ? govPalette.muted : govPalette.veryDim,
                    whiteSpace: "nowrap",
                    maxWidth: 80,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {scenario.title}
                </div>
              </div>
            </button>

            {i < scenarios.length - 1 && (
              <div
                style={{
                  width: 32,
                  height: 2,
                  background: isCompleted ? `${govPalette.allow}40` : govPalette.border,
                  transition: "background 0.3s",
                }}
              />
            )}
          </div>
        );
      })}

      {/* Epilogue node */}
      <div style={{ display: "flex", alignItems: "center" }}>
        <div
          style={{
            width: 32,
            height: 2,
            background: completedIndices.size === scenarios.length ? `${govPalette.allow}40` : govPalette.border,
          }}
        />
        <button
          onClick={() => completedIndices.size === scenarios.length && onEpilogue()}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 6,
            background: "none",
            border: "none",
            cursor: completedIndices.size === scenarios.length ? "pointer" : "default",
            opacity: completedIndices.size === scenarios.length ? 1 : 0.3,
            padding: "4px 8px",
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              background: showEpilogue ? govPalette.accent : govPalette.cardAlt,
              border: `2px solid ${showEpilogue ? govPalette.accent : govPalette.border}`,
              color: showEpilogue ? "#fff" : govPalette.text,
            }}
          >
            {"\ud83d\udcca"}
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: showEpilogue ? govPalette.text : govPalette.dim }}>
              Summary
            </div>
            <div style={{ fontSize: 9, color: govPalette.veryDim }}>Ledger</div>
          </div>
        </button>
      </div>
    </div>
  );
}

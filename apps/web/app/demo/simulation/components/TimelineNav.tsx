"use client";

import type { ScenarioConfig } from "../types";

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
            {/* Node */}
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
                    ? "#6366f1"
                    : isCompleted
                    ? "#22c55e20"
                    : "#1a1b1e",
                  border: `2px solid ${
                    isActive ? "#6366f1" : isCompleted ? "#22c55e" : "#27272a"
                  }`,
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
                    color: isActive ? "#f4f4f5" : "#71717a",
                    whiteSpace: "nowrap",
                  }}
                >
                  {scenario.time}
                </div>
                <div
                  style={{
                    fontSize: 9,
                    color: isActive ? "#a1a1aa" : "#52525b",
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

            {/* Connector line */}
            {i < scenarios.length - 1 && (
              <div
                style={{
                  width: 32,
                  height: 2,
                  background: isCompleted ? "#22c55e40" : "#27272a",
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
            background: completedIndices.size === scenarios.length ? "#22c55e40" : "#27272a",
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
              background: showEpilogue ? "#6366f1" : "#1a1b1e",
              border: `2px solid ${showEpilogue ? "#6366f1" : "#27272a"}`,
            }}
          >
            {"\ud83d\udcca"}
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: showEpilogue ? "#f4f4f5" : "#71717a" }}>
              Summary
            </div>
            <div style={{ fontSize: 9, color: "#52525b" }}>Ledger</div>
          </div>
        </button>
      </div>
    </div>
  );
}

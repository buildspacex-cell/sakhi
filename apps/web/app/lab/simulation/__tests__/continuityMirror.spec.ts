import test from "node:test";
import assert from "node:assert/strict";

import { makeAnchorLine, makeRecap, makeMirrorTitle } from "../continuityMirror";
import type { CompiledContinuityArc } from "../types";

function makeArc(overrides: Partial<CompiledContinuityArc> = {}): CompiledContinuityArc {
  return {
    id: "arc_test",
    key: "sakhi",
    start_ts: "2025-11-18T00:00:00Z",
    end_ts: "2026-02-26T00:00:00Z",
    span_days: 100.3,
    element_count: 12,
    phase_count: 3,
    phases: [
      {
        index: 0,
        start_ts: "2025-11-18T00:00:00Z",
        end_ts: "2025-12-12T00:00:00Z",
        start_day: 1,
        end_day: 24,
        element_count: 4,
        stats: {},
      },
      {
        index: 1,
        start_ts: "2025-12-13T00:00:00Z",
        end_ts: "2026-01-18T00:00:00Z",
        start_day: 25,
        end_day: 62,
        element_count: 4,
        stats: {},
      },
      {
        index: 2,
        start_ts: "2026-01-19T00:00:00Z",
        end_ts: "2026-02-26T00:00:00Z",
        start_day: 63,
        end_day: 103,
        element_count: 4,
        stats: {},
      },
    ],
    features: {
      direction: "rising",
      stability: 0.64,
      oscillation: 0.24,
      momentum: 0.18,
      average_rate: 0.03,
      density: 0.08,
      change_points: [1],
    },
    event_refs: [],
    ...overrides,
  };
}

test("makeMirrorTitle rounds the visible span", () => {
  assert.equal(makeMirrorTitle("Sakhi", makeArc()), "Sakhi — One unfolding over ~100 days");
});

test("makeAnchorLine reflects visible pivots without moral framing", () => {
  assert.equal(
    makeAnchorLine(makeArc()),
    "One continuous thread with one visible pivot.",
  );
});

test("makeAnchorLine highlights back-and-forth when oscillation is high", () => {
  assert.equal(
    makeAnchorLine(
      makeArc({
        features: {
          direction: "flat",
          stability: 0.35,
          oscillation: 0.72,
          momentum: null,
          average_rate: null,
          density: 0.08,
          change_points: [1, 2],
        },
      }),
    ),
    "Recurring return to the same theme, with 2 visible pivots.",
  );
});

test("makeAnchorLine stays within the required character limit", () => {
  assert.ok(makeAnchorLine(makeArc()).length <= 120);
});

test("makeAnchorLine treats a stable arc as a preserved core thread", () => {
  assert.equal(
    makeAnchorLine(
      makeArc({
        features: {
          direction: "flat",
          stability: 0.82,
          oscillation: 0.18,
          momentum: null,
          average_rate: null,
          density: 0.08,
          change_points: [1, 2],
        },
      }),
    ),
    "The core thread stayed intact; focus reorganized twice.",
  );
});

test("makeRecap falls back to structural descriptors when tags are missing", () => {
  assert.deepEqual(makeRecap(makeArc()), {
    start: "Started with a steady thread.",
    pivots: "Then one pivot reorganized the thread.",
    current: "Now holding a more consistent thread.",
  });
});

test("makeRecap uses available phase tags when confidence is strong", () => {
  const recap = makeRecap(
    makeArc({
      phases: [
        {
          index: 0,
          start_ts: "2025-11-18T00:00:00Z",
          end_ts: "2025-12-12T00:00:00Z",
          start_day: 1,
          end_day: 24,
          element_count: 3,
          stats: { dominant_tag: { label: "ayurveda_personalization", confidence: 0.92 } },
        },
        {
          index: 1,
          start_ts: "2025-12-13T00:00:00Z",
          end_ts: "2026-01-18T00:00:00Z",
          start_day: 25,
          end_day: 62,
          element_count: 5,
          stats: { dominant_tag: { label: "clarity", confidence: 0.86 } },
        },
        {
          index: 2,
          start_ts: "2026-01-19T00:00:00Z",
          end_ts: "2026-02-26T00:00:00Z",
          start_day: 63,
          end_day: 103,
          element_count: 4,
          stats: { dominant_tag: { label: "deterministic_continuity", confidence: 0.9 } },
        },
      ],
    }),
  );

  assert.deepEqual(recap, {
    start: "Started around ayurveda personalization.",
    pivots: "Then pivoted toward clarity.",
    current: "Now centered on deterministic continuity.",
  });
});

test("makeRecap degrades gracefully to a single-span fallback", () => {
  assert.deepEqual(
    makeRecap(
      makeArc({
        phase_count: 0,
        phases: [],
        features: null,
      }),
    ),
    {
      start: "Started with a steady thread.",
      pivots: "No sharp pivots; the thread shifted gradually.",
      current: "Now holding a more consistent thread.",
    },
  );
});

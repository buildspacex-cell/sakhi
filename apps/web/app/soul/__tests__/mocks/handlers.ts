import { rest } from "msw";

export const handlers = [
  rest.get("/soul/state/demo", (_req, res, ctx) =>
    res(
      ctx.json({
        core_values: ["growth", "balance"],
        identity_themes: ["learning"],
        longing: ["rest"],
        aversions: ["burnout"],
        commitments: ["daily practice"],
        shadow: ["doubt"],
        light: ["optimism"],
        confidence: 0.6,
      })
    )
  ),
  rest.get("/soul/summary/demo", (_req, res, ctx) =>
    res(
      ctx.json({
        top_shadow: ["doubt"],
        top_light: ["optimism"],
        dominant_friction: "balance vs overwork",
        coherence_score: 0.7,
      })
    )
  ),
  rest.get("/soul/timeline/demo", (_req, res, ctx) =>
    res(
      ctx.json([
        { ts: "t1", shadow: [1], light: [2], conflict: [1], friction: [2] },
        { ts: "t2", shadow: [2], light: [1], conflict: [1], friction: [1] },
      ])
    )
  ),
  rest.get("/soul/narrative/demo", (_req, res, ctx) =>
    res(
      ctx.json({
        identity_arc: "testing arc",
        soul_archetype: "sage",
        life_phase: "growth",
        value_conflicts: ["balance vs overwork"],
        healing_direction: ["rest more"],
        narrative_tension: "medium",
      })
    )
  ),
  rest.get("/soul/alignment/demo", (_req, res, ctx) =>
    res(
      ctx.json({
        alignment_score: 0.6,
        conflict_zones: ["overwork"],
        action_suggestions: ["take a break"],
      })
    )
  ),
];

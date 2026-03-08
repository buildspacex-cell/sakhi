import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const clientPath = join(process.cwd(), "apps/web/app/lab/simulation/client.tsx");

test("arc detail keeps the explainability anchor and existing detail markers", () => {
  const source = readFileSync(clientPath, "utf8");

  assert.match(source, /id="arc-detail"/);
  assert.match(source, /Arc Detail/);
  assert.match(source, /Continuity Spine/);
  assert.match(source, /Day \{event\.day\}/);
});

type JudgeResult = {
  pass: boolean;
  reasons: string[];
};

type JudgeInput = {
  reflectionText: string;
  episodes: string[]; // verbatim or trimmed journal excerpts
};

const BANNED_PHRASES = [
  /ups and downs/i,
  /mixed experiences?/i,
  /small victories?/i,
  /on the bright side/i,
  /silver lining/i,
  /took a back seat/i,
  /\bshould\b/i,
  /\bneed to\b/i,
  /\bmust\b/i,
  /\blesson\b/i,
  /\bgrowth\b/i,
  /\blearning\b/i,
  /\bled to\b/i,
  /\bcaused\b/i,
  /\bresulted in\b/i,
];

const HEADING_PATTERN = /^\s*(#+|\*\*|__|\b(body|emotion|energy|work|mind)\b)/im;

const BULLET_PATTERN = /^\s*[-*•]/m;

/**
 * Simple grounding check:
 * Ensures reflection is not generic by requiring
 * overlap with episode vocabulary.
 */
function hasConceptualGrounding(reflection: string, episodes: string[]): boolean {
  const reflectionTokens = tokenize(reflection);
  const episodeTokens = tokenize(episodes.join(" "));

  let overlapCount = 0;

  for (const token of reflectionTokens) {
    if (episodeTokens.has(token)) {
      overlapCount++;
      if (overlapCount >= 3) return true; // minimal grounding threshold
    }
  }

  return false;
}

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, "")
      .split(/\s+/)
      .filter((t) => t.length > 4), // ignore filler words
  );
}

export function judgeWeeklyReflection(input: JudgeInput): JudgeResult {
  const reasons: string[] = [];
  const text = input.reflectionText.trim();

  // 1. Empty or too short
  if (text.length < 100) {
    reasons.push("Reflection is too short to be meaningful");
  }

  // 2. Banned phrase scan
  for (const pattern of BANNED_PHRASES) {
    if (pattern.test(text)) {
      reasons.push(`Contains banned language: ${pattern}`);
    }
  }

  // 3. Advice / causality scan (extra guard)
  if (/\b(because|therefore|so that)\b/i.test(text)) {
    reasons.push("Contains causal or explanatory language");
  }

  // 4. Sectioning / formatting violations
  if (HEADING_PATTERN.test(text)) {
    reasons.push("Contains headings or section labels");
  }

  if (BULLET_PATTERN.test(text)) {
    reasons.push("Contains bullet points or list formatting");
  }

  // 5. Conceptual grounding check
  if (!hasConceptualGrounding(text, input.episodes)) {
    reasons.push("Reflection appears generic and not grounded in episodes");
  }

  return {
    pass: reasons.length === 0,
    reasons,
  };
}

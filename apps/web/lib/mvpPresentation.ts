import { promises as fs } from "fs";
import path from "path";

const PRESENTATION_DIR_CANDIDATES = [
  path.join(process.cwd(), "docs", "MVP Release"),
  path.join(process.cwd(), "..", "..", "docs", "MVP Release"),
  path.join(process.cwd(), "..", "docs", "MVP Release"),
];

const MVP_ASSET_FILES = {
  chat: "chat.PNG",
  reflection: "reflection.PNG",
  moments: "moments.PNG",
  "moments-detail": "moments-detail.PNG",
  "vidz-space": "vidz-space.PNG",
} as const;

type MvpAssetSlug = keyof typeof MVP_ASSET_FILES;

let cachedPresentationDir: string | null = null;

async function resolvePresentationDir() {
  if (cachedPresentationDir) {
    return cachedPresentationDir;
  }

  for (const candidate of PRESENTATION_DIR_CANDIDATES) {
    try {
      await fs.access(candidate);
      cachedPresentationDir = candidate;
      return candidate;
    } catch {
      continue;
    }
  }

  throw new Error("Unable to locate docs/MVP Release for web presentation.");
}

function rewriteAssetPaths(html: string) {
  return Object.entries(MVP_ASSET_FILES).reduce((output, [slug, fileName]) => {
    return output.replaceAll(`./${fileName}`, `/mvp-release/assets/${slug}`);
  }, html);
}

export async function getMvpPresentationHtml() {
  const presentationDir = await resolvePresentationDir();
  const htmlPath = path.join(presentationDir, "mvp-presentation.html");
  const html = await fs.readFile(htmlPath, "utf8");
  return rewriteAssetPaths(html);
}

export async function getMvpPresentationAsset(slug: string) {
  if (!(slug in MVP_ASSET_FILES)) {
    return null;
  }

  const presentationDir = await resolvePresentationDir();
  const fileName = MVP_ASSET_FILES[slug as MvpAssetSlug];
  const assetPath = path.join(presentationDir, fileName);
  const buffer = await fs.readFile(assetPath);

  return {
    buffer,
    contentType: "image/png",
  };
}

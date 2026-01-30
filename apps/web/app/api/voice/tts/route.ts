import { NextRequest, NextResponse } from "next/server";
import OpenAI from "openai";

// Force dynamic to avoid build-time initialization without env vars
export const dynamic = "force-dynamic";

// =============================================================================
// TTS ENDPOINT
// Converts text to speech using OpenAI TTS
// =============================================================================

// Lazy initialization to avoid build-time errors
let openai: OpenAI | null = null;
function getOpenAI() {
  if (!openai) {
    openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  }
  return openai;
}

// Voice options for different tones
const VOICE_OPTIONS = {
  default: "nova",      // Warm, friendly - default for Sakhi
  calm: "shimmer",      // Soft, calming
  energetic: "alloy",   // Clear, neutral
  warm: "nova",         // Expressive, warm
} as const;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { text, voice = "default", speed = 1.0 } = body;

    if (!text) {
      return NextResponse.json(
        { error: "No text provided" },
        { status: 400 }
      );
    }

    // Limit text length to prevent abuse
    const truncatedText = text.slice(0, 4096);

    // Select voice
    const selectedVoice = VOICE_OPTIONS[voice as keyof typeof VOICE_OPTIONS] || VOICE_OPTIONS.default;

    console.log(`[voice/tts] Generating TTS for ${truncatedText.length} chars with voice: ${selectedVoice}`);

    const ttsResponse = await getOpenAI().audio.speech.create({
      model: "tts-1",
      voice: selectedVoice,
      input: truncatedText,
      response_format: "mp3",
      speed: Math.max(0.25, Math.min(4.0, speed)), // Clamp speed
    });

    // Convert to base64 data URL
    const audioArrayBuffer = await ttsResponse.arrayBuffer();
    const audioBase64 = Buffer.from(audioArrayBuffer).toString("base64");
    const audioDataUrl = `data:audio/mp3;base64,${audioBase64}`;

    return NextResponse.json({
      audio_url: audioDataUrl,
      text: truncatedText,
      voice: selectedVoice,
    });
  } catch (error) {
    console.error("[voice/tts] Error:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "TTS generation failed",
      },
      { status: 500 }
    );
  }
}

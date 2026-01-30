import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from "@/lib/api-base";
import OpenAI from "openai";

// =============================================================================
// VOICE TURN ENDPOINT
// Pipeline: Audio → Whisper STT → Sakhi Turn API → OpenAI TTS → Audio
// =============================================================================

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(req: NextRequest) {
  try {
    // Parse multipart form data
    const formData = await req.formData();
    const audioFile = formData.get("audio") as File | null;
    const personId = formData.get("person_id") as string | null;

    if (!audioFile) {
      return NextResponse.json(
        { error: "No audio file provided" },
        { status: 400 }
      );
    }

    if (!personId) {
      return NextResponse.json(
        { error: "No person_id provided" },
        { status: 400 }
      );
    }

    // ==========================================================================
    // STEP 1: Transcribe audio with Whisper
    // ==========================================================================
    console.log("[voice/turn] Transcribing audio...");

    // Convert File to buffer for OpenAI
    const audioBuffer = await audioFile.arrayBuffer();
    const audioBlob = new Blob([audioBuffer], { type: audioFile.type });

    // Create a File object that OpenAI SDK can handle
    const transcriptionFile = new File([audioBlob], "audio.webm", {
      type: audioFile.type || "audio/webm",
    });

    const transcription = await openai.audio.transcriptions.create({
      file: transcriptionFile,
      model: "whisper-1",
      language: "en",
      response_format: "json",
    });

    const transcript = transcription.text?.trim();
    console.log("[voice/turn] Transcript:", transcript);

    if (!transcript) {
      return NextResponse.json({
        transcript: "",
        reply: null,
        audio_url: null,
        message: "No speech detected",
      });
    }

    // ==========================================================================
    // STEP 2: Send to Sakhi Turn API
    // ==========================================================================
    console.log("[voice/turn] Calling Sakhi turn API...");

    const apiBase = getApiBase();
    const turnResponse = await fetch(
      `${apiBase}/v2/turn?user=${encodeURIComponent(personId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: transcript, source: "voice" }),
      }
    );

    if (!turnResponse.ok) {
      const errorText = await turnResponse.text();
      console.error("[voice/turn] Turn API error:", errorText);
      return NextResponse.json({
        transcript,
        reply: null,
        audio_url: null,
        error: "Turn API failed",
      });
    }

    const turnData = await turnResponse.json();
    const reply = turnData.reply;
    console.log("[voice/turn] Reply:", reply?.slice(0, 100) + "...");

    if (!reply) {
      return NextResponse.json({
        transcript,
        reply: null,
        audio_url: null,
        turn_data: turnData,
      });
    }

    // ==========================================================================
    // STEP 3: Generate TTS for response
    // ==========================================================================
    console.log("[voice/turn] Generating TTS...");

    const ttsResponse = await openai.audio.speech.create({
      model: "tts-1",
      voice: "nova", // Warm, friendly female voice - fits Sakhi's tone
      input: reply,
      response_format: "mp3",
      speed: 1.0,
    });

    // Convert to base64 data URL
    const audioArrayBuffer = await ttsResponse.arrayBuffer();
    const audioBase64 = Buffer.from(audioArrayBuffer).toString("base64");
    const audioDataUrl = `data:audio/mp3;base64,${audioBase64}`;

    console.log("[voice/turn] TTS complete, returning response");

    return NextResponse.json({
      transcript,
      reply,
      audio_url: audioDataUrl,
      turn_data: turnData,
    });
  } catch (error) {
    console.error("[voice/turn] Error:", error);
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Voice processing failed",
      },
      { status: 500 }
    );
  }
}

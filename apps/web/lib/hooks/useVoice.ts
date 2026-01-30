"use client";

import { useState, useRef, useCallback, useEffect } from "react";

// =============================================================================
// TYPES
// =============================================================================

export type VoiceState =
  | "idle"           // Ready to start
  | "recording"      // Capturing audio
  | "processing"     // STT in progress
  | "speaking"       // TTS playback
  | "error";         // Something went wrong

export interface VoiceTranscript {
  text: string;
  confidence?: number;
  isFinal: boolean;
}

export interface VoiceResponse {
  text: string;        // Sakhi's response text
  audioUrl?: string;   // TTS audio URL (if available)
}

export interface UseVoiceOptions {
  personId: string;
  onTranscript?: (transcript: VoiceTranscript) => void;
  onResponse?: (response: VoiceResponse) => void;
  onError?: (error: Error) => void;
  onStateChange?: (state: VoiceState) => void;
  autoPlayResponse?: boolean;
}

export interface UseVoiceReturn {
  state: VoiceState;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  transcript: string;
  response: string | null;
  error: Error | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  cancelRecording: () => void;
  playResponse: () => Promise<void>;
  stopPlayback: () => void;
}

// =============================================================================
// HOOK
// =============================================================================

export function useVoice(options: UseVoiceOptions): UseVoiceReturn {
  const {
    personId,
    onTranscript,
    onResponse,
    onError,
    onStateChange,
    autoPlayResponse = true,
  } = options;

  // State
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Update state and notify
  const updateState = useCallback(
    (newState: VoiceState) => {
      setState(newState);
      onStateChange?.(newState);
    },
    [onStateChange]
  );

  // Handle errors
  const handleError = useCallback(
    (err: Error) => {
      setError(err);
      updateState("error");
      onError?.(err);
    },
    [updateState, onError]
  );

  // Clean up audio resources
  const cleanupAudio = useCallback(() => {
    if (audioSourceRef.current) {
      try {
        audioSourceRef.current.stop();
      } catch {
        // Ignore if already stopped
      }
      audioSourceRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // Ignore
        }
      }
      mediaRecorderRef.current = null;
    }
    audioChunksRef.current = [];
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [cleanupAudio]);

  // Play audio from URL (declared early so stopRecording can reference it)
  const playAudioFromUrl = useCallback(async (url: string) => {
    try {
      // Initialize AudioContext if needed
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioContext = audioContextRef.current;

      // Fetch and decode audio
      const audioRes = await fetch(url);
      const arrayBuffer = await audioRes.arrayBuffer();
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      // Create and play source
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);

      audioSourceRef.current = source;

      return new Promise<void>((resolve) => {
        source.onended = () => {
          audioSourceRef.current = null;
          resolve();
        };
        source.start();
      });
    } catch (err) {
      console.error("Audio playback error:", err);
      throw err;
    }
  }, []);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      // Reset state
      setTranscript("");
      setResponse(null);
      setError(null);
      audioChunksRef.current = [];

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      // Create MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      // Collect audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Start recording
      mediaRecorder.start(250); // Collect data every 250ms
      updateState("recording");
    } catch (err) {
      handleError(
        err instanceof Error
          ? err
          : new Error("Failed to start recording")
      );
    }
  }, [updateState, handleError]);

  // Stop recording and process
  const stopRecording = useCallback(async () => {
    const mediaRecorder = mediaRecorderRef.current;
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      return;
    }

    return new Promise<void>((resolve) => {
      mediaRecorder.onstop = async () => {
        // Stop the stream
        streamRef.current?.getTracks().forEach((track) => track.stop());

        // Create blob from chunks
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType,
        });

        if (audioBlob.size === 0) {
          handleError(new Error("No audio recorded"));
          resolve();
          return;
        }

        // Process audio
        updateState("processing");

        try {
          // Send to voice API
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.webm");
          formData.append("person_id", personId);

          const res = await fetch("/api/voice/turn", {
            method: "POST",
            body: formData,
          });

          if (!res.ok) {
            const errorText = await res.text();
            throw new Error(errorText || "Voice processing failed");
          }

          const data = await res.json();

          // Update transcript
          if (data.transcript) {
            setTranscript(data.transcript);
            onTranscript?.({
              text: data.transcript,
              confidence: data.confidence,
              isFinal: true,
            });
          }

          // Update response
          if (data.reply) {
            setResponse(data.reply);
            onResponse?.({
              text: data.reply,
              audioUrl: data.audio_url,
            });

            // Auto-play response if enabled
            if (autoPlayResponse && data.audio_url) {
              updateState("speaking");
              await playAudioFromUrl(data.audio_url);
              updateState("idle");
            } else {
              updateState("idle");
            }
          } else {
            updateState("idle");
          }
        } catch (err) {
          handleError(
            err instanceof Error
              ? err
              : new Error("Failed to process audio")
          );
        }

        resolve();
      };

      mediaRecorder.stop();
    });
  }, [
    personId,
    updateState,
    handleError,
    onTranscript,
    onResponse,
    autoPlayResponse,
    playAudioFromUrl,
  ]);

  // Cancel recording without processing
  const cancelRecording = useCallback(() => {
    cleanupAudio();
    updateState("idle");
  }, [cleanupAudio, updateState]);

  // Play the current response
  const playResponse = useCallback(async () => {
    if (!response) return;

    updateState("speaking");
    try {
      // Generate TTS for current response
      const res = await fetch("/api/voice/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: response }),
      });

      if (!res.ok) {
        throw new Error("TTS generation failed");
      }

      const data = await res.json();
      if (data.audio_url) {
        await playAudioFromUrl(data.audio_url);
      }
    } catch (err) {
      console.error("Playback error:", err);
    } finally {
      updateState("idle");
    }
  }, [response, updateState, playAudioFromUrl]);

  // Stop playback
  const stopPlayback = useCallback(() => {
    if (audioSourceRef.current) {
      try {
        audioSourceRef.current.stop();
      } catch {
        // Ignore
      }
      audioSourceRef.current = null;
    }
    updateState("idle");
  }, [updateState]);

  return {
    state,
    isRecording: state === "recording",
    isProcessing: state === "processing",
    isSpeaking: state === "speaking",
    transcript,
    response,
    error,
    startRecording,
    stopRecording,
    cancelRecording,
    playResponse,
    stopPlayback,
  };
}

export default useVoice;

import { useState, useRef, useCallback, useEffect } from "react";
import { Audio, PermissionStatus } from "expo-av";
import * as FileSystem from "expo-file-system";
import * as Linking from "expo-linking";

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
  text: string;
  audioUrl?: string;
}

export interface UseVoiceOptions {
  personId: string;
  /** FastAPI backend URL (e.g., http://192.168.1.x:8080 for local dev) */
  backendUrl: string;
  /** OpenAI API key for STT/TTS (passed from app config) */
  openaiApiKey: string;
  onTranscript?: (transcript: VoiceTranscript) => void;
  onResponse?: (response: VoiceResponse) => void;
  onError?: (error: Error) => void;
  onStateChange?: (state: VoiceState) => void;
  autoPlayResponse?: boolean;
  voice?: "nova" | "shimmer" | "alloy";
  speed?: number;
}

export type PermissionState = "undetermined" | "denied" | "granted";

export interface UseVoiceReturn {
  state: VoiceState;
  isRecording: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  transcript: string;
  response: string | null;
  error: Error | null;
  permissionState: PermissionState;
  checkPermission: () => Promise<PermissionState>;
  requestPermission: () => Promise<PermissionState>;
  openSettings: () => Promise<void>;
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
    backendUrl,
    openaiApiKey,
    onTranscript,
    onResponse,
    onError,
    onStateChange,
    autoPlayResponse = true,
    voice = "nova",
    speed = 1.0,
  } = options;

  // State
  const [state, setState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [permissionState, setPermissionState] = useState<PermissionState>("undetermined");

  // Refs
  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);

  // Check permission status without requesting
  const checkPermission = useCallback(async (): Promise<PermissionState> => {
    const { status } = await Audio.getPermissionsAsync();
    let state: PermissionState;
    if (status === PermissionStatus.GRANTED) {
      state = "granted";
    } else if (status === PermissionStatus.DENIED) {
      state = "denied";
    } else {
      state = "undetermined";
    }
    setPermissionState(state);
    return state;
  }, []);

  // Request permission
  const requestPermission = useCallback(async (): Promise<PermissionState> => {
    const { status } = await Audio.requestPermissionsAsync();
    let state: PermissionState;
    if (status === PermissionStatus.GRANTED) {
      state = "granted";
    } else if (status === PermissionStatus.DENIED) {
      state = "denied";
    } else {
      state = "undetermined";
    }
    setPermissionState(state);
    return state;
  }, []);

  // Open app settings
  const openSettings = useCallback(async () => {
    await Linking.openSettings();
  }, []);

  // Check permission on mount
  useEffect(() => {
    checkPermission();
  }, [checkPermission]);

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

  // Cleanup audio resources
  const cleanupAudio = useCallback(async () => {
    if (soundRef.current) {
      try {
        await soundRef.current.unloadAsync();
      } catch {
        // Ignore
      }
      soundRef.current = null;
    }
    if (recordingRef.current) {
      try {
        await recordingRef.current.stopAndUnloadAsync();
      } catch {
        // Ignore
      }
      recordingRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  // Request audio permissions and set audio mode
  const requestPermissions = useCallback(async () => {
    const status = await requestPermission();
    if (status !== "granted") {
      throw new Error("Microphone permission not granted");
    }
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });
  }, [requestPermission]);

  // Play audio from URL
  const playAudioFromUrl = useCallback(async (url: string) => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      });

      const { sound } = await Audio.Sound.createAsync(
        { uri: url },
        { shouldPlay: true }
      );
      soundRef.current = sound;

      return new Promise<void>((resolve) => {
        sound.setOnPlaybackStatusUpdate((status) => {
          if (status.isLoaded && status.didJustFinish) {
            soundRef.current = null;
            resolve();
          }
        });
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

      // Request permissions
      await requestPermissions();

      // Start recording
      const recording = new Audio.Recording();
      await recording.prepareToRecordAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      await recording.startAsync();
      recordingRef.current = recording;

      updateState("recording");
    } catch (err) {
      handleError(
        err instanceof Error ? err : new Error("Failed to start recording")
      );
    }
  }, [updateState, handleError, requestPermissions]);

  // Stop recording and process
  const stopRecording = useCallback(async () => {
    const recording = recordingRef.current;
    if (!recording) {
      return;
    }

    try {
      // Stop recording
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      recordingRef.current = null;

      if (!uri) {
        handleError(new Error("No audio recorded"));
        return;
      }

      // Process audio
      updateState("processing");

      // Step 1: Call OpenAI Whisper for STT
      const sttFormData = new FormData();
      sttFormData.append("file", {
        uri: uri,
        type: "audio/m4a",
        name: "recording.m4a",
      } as unknown as Blob);
      sttFormData.append("model", "whisper-1");

      const sttRes = await fetch("https://api.openai.com/v1/audio/transcriptions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${openaiApiKey}`,
        },
        body: sttFormData,
      });

      if (!sttRes.ok) {
        const errorText = await sttRes.text();
        throw new Error(errorText || "Speech-to-text failed");
      }

      const sttData = await sttRes.json();
      const transcriptText = sttData.text;

      if (!transcriptText) {
        throw new Error("No speech detected");
      }

      // Update transcript
      setTranscript(transcriptText);
      onTranscript?.({
        text: transcriptText,
        isFinal: true,
      });

      // Step 2: Call FastAPI backend for conversation turn
      const turnRes = await fetch(`${backendUrl}/v2/turn?user=${personId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          text: transcriptText,
        }),
      });

      if (!turnRes.ok) {
        const errorText = await turnRes.text();
        throw new Error(errorText || "Conversation turn failed");
      }

      const turnData = await turnRes.json();
      const replyText = turnData.reply || turnData.message;

      if (!replyText) {
        updateState("idle");
        return;
      }

      // Update response
      setResponse(replyText);
      onResponse?.({
        text: replyText,
      });

      // Step 3: Call OpenAI TTS if autoPlayResponse is enabled
      if (autoPlayResponse) {
        updateState("speaking");

        const ttsRes = await fetch("https://api.openai.com/v1/audio/speech", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${openaiApiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "tts-1",
            input: replyText,
            voice: voice,
            speed: speed,
          }),
        });

        if (ttsRes.ok) {
          // Save audio to temp file and play
          const audioBlob = await ttsRes.blob();
          const reader = new FileReader();
          const base64Audio = await new Promise<string>((resolve) => {
            reader.onloadend = () => {
              const result = reader.result as string;
              resolve(result.split(",")[1]);
            };
            reader.readAsDataURL(audioBlob);
          });

          const audioUri = FileSystem.cacheDirectory + "response.mp3";
          await FileSystem.writeAsStringAsync(audioUri, base64Audio, {
            encoding: FileSystem.EncodingType.Base64,
          });

          await playAudioFromUrl(audioUri);
          await FileSystem.deleteAsync(audioUri, { idempotent: true });
        }
        updateState("idle");
      } else {
        updateState("idle");
      }

      // Clean up temp file
      await FileSystem.deleteAsync(uri, { idempotent: true });
    } catch (err) {
      handleError(
        err instanceof Error ? err : new Error("Failed to process audio")
      );
    }
  }, [
    personId,
    backendUrl,
    openaiApiKey,
    voice,
    speed,
    updateState,
    handleError,
    onTranscript,
    onResponse,
    autoPlayResponse,
    playAudioFromUrl,
  ]);

  // Cancel recording without processing
  const cancelRecording = useCallback(async () => {
    await cleanupAudio();
    updateState("idle");
  }, [cleanupAudio, updateState]);

  // Play the current response
  const playResponse = useCallback(async () => {
    if (!response) return;

    updateState("speaking");
    try {
      // Generate TTS using OpenAI directly
      const ttsRes = await fetch("https://api.openai.com/v1/audio/speech", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${openaiApiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "tts-1",
          input: response,
          voice: voice,
          speed: speed,
        }),
      });

      if (!ttsRes.ok) {
        throw new Error("TTS generation failed");
      }

      // Save audio to temp file and play
      const audioBlob = await ttsRes.blob();
      const reader = new FileReader();
      const base64Audio = await new Promise<string>((resolve) => {
        reader.onloadend = () => {
          const result = reader.result as string;
          resolve(result.split(",")[1]);
        };
        reader.readAsDataURL(audioBlob);
      });

      const audioUri = FileSystem.cacheDirectory + "response_replay.mp3";
      await FileSystem.writeAsStringAsync(audioUri, base64Audio, {
        encoding: FileSystem.EncodingType.Base64,
      });

      await playAudioFromUrl(audioUri);
      await FileSystem.deleteAsync(audioUri, { idempotent: true });
    } catch (err) {
      console.error("Playback error:", err);
    } finally {
      updateState("idle");
    }
  }, [response, openaiApiKey, voice, speed, updateState, playAudioFromUrl]);

  // Stop playback
  const stopPlayback = useCallback(async () => {
    if (soundRef.current) {
      try {
        await soundRef.current.stopAsync();
      } catch {
        // Ignore
      }
      soundRef.current = null;
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
    permissionState,
    checkPermission,
    requestPermission,
    openSettings,
    startRecording,
    stopRecording,
    cancelRecording,
    playResponse,
    stopPlayback,
  };
}

export default useVoice;

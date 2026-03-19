import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  Animated,
  Easing,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  AppState,
  AppStateStatus,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useVoice, VoiceState, PermissionState } from "../hooks/useVoice";
import { useAuth } from "../lib/auth/AuthContext";

// =============================================================================
// CONFIG
// =============================================================================

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || "http://localhost:8080";
const OPENAI_API_KEY = process.env.EXPO_PUBLIC_OPENAI_API_KEY || "";

// =============================================================================
// PALETTE
// =============================================================================

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#71717a",
  subtle: "#52525b",
  faint: "#3f3f46",
  accent: "#6366f1",
  accentDim: "rgba(99, 102, 241, 0.12)",
  cardBg: "#141416",
  border: "#1f1f23",
  recording: "#ef4444",
  processing: "#f59e0b",
  speaking: "#22c55e",
};

// =============================================================================
// TYPES
// =============================================================================

interface Message {
  id: string;
  type: "user" | "sakhi";
  text: string;
  timestamp: Date;
}

// =============================================================================
// VOICE SCREEN
// =============================================================================

export default function VoiceScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [textInput, setTextInput] = useState("");
  const scrollViewRef = useRef<ScrollView>(null);
  const { user } = useAuth();
  const personId = user?.personId || "";
  const isAuthReady = !!personId;

  const voice = useVoice({
    personId,
    backendUrl: BACKEND_URL,
    openaiApiKey: OPENAI_API_KEY,
    autoPlayResponse: true,
  });

  // Re-check permission when app returns from background (e.g., after settings)
  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextAppState: AppStateStatus) => {
      if (nextAppState === "active") {
        voice.checkPermission();
      }
    });
    return () => subscription.remove();
  }, [voice.checkPermission]);

  // Add messages when voice interaction completes
  useEffect(() => {
    const replyText = voice.response;
    if (voice.transcript && replyText) {
      const userExists = messages.some(
        (m) => m.type === "user" && m.text === voice.transcript
      );
      if (!userExists) {
        setMessages((prev) => [
          ...prev,
          {
            id: `user-${Date.now()}`,
            type: "user",
            text: voice.transcript,
            timestamp: new Date(),
          },
          {
            id: `sakhi-${Date.now()}`,
            type: "sakhi",
            text: replyText,
            timestamp: new Date(),
          },
        ]);
      }
    }
  }, [voice.transcript, voice.response, messages]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  const handleVoiceButton = async () => {
    if (!isAuthReady) {
      return;
    }

    // If permission denied, open settings
    if (voice.permissionState === "denied") {
      await voice.openSettings();
      return;
    }

    // If permission undetermined, request it first
    if (voice.permissionState === "undetermined") {
      const result = await voice.requestPermission();
      if (result !== "granted") {
        return;
      }
    }

    // Normal voice button behavior
    if (voice.isRecording) {
      await voice.stopRecording();
    } else if (voice.isSpeaking) {
      voice.stopPlayback();
    } else if (!voice.isProcessing) {
      await voice.startRecording();
    }
  };

  const handleTextSubmit = () => {
    if (textInput.trim() && isAuthReady) {
      // For now, just add as user message
      // In future, this would call the backend
      setMessages((prev) => [
        ...prev,
        {
          id: `user-${Date.now()}`,
          type: "user",
          text: textInput.trim(),
          timestamp: new Date(),
        },
      ]);
      setTextInput("");
    }
  };

  const hasStarted = messages.length > 0 || voice.isRecording || voice.isProcessing;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header - stable, non-interactive */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Sakhi</Text>
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        {/* Conversation Area */}
        <ScrollView
          ref={scrollViewRef}
          style={styles.conversationArea}
          contentContainerStyle={[
            styles.conversationContent,
            !hasStarted && styles.conversationContentEmpty,
          ]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Empty State - before first message */}
          {!hasStarted && (
            <View style={styles.emptyState}>
          {voice.permissionState === "denied" ? (
                <>
                  <Text style={styles.primaryPrompt}>
                    Sakhi needs microphone access to listen.
                  </Text>
                  <Text style={styles.subtleHint}>
                    Tap the mic button to open Settings.
                  </Text>
                </>
              ) : !isAuthReady ? (
                <>
                  <Text style={styles.primaryPrompt}>
                    Sign in to start talking with Sakhi.
                  </Text>
                  <Text style={styles.subtleHint}>
                    Voice replies need your account context first.
                  </Text>
                </>
              ) : voice.permissionState === "undetermined" ? (
                <>
                  <Text style={styles.primaryPrompt}>
                    I'm here. What's present right now?
                  </Text>
                  <Text style={styles.subtleHint}>
                    Tap the mic to allow Sakhi to listen.
                  </Text>
                </>
              ) : (
                <>
                  <Text style={styles.primaryPrompt}>
                    I'm here. What's present right now?
                  </Text>
                  <Text style={styles.subtleHint}>
                    You can speak — or type if you prefer.
                  </Text>
                </>
              )}
            </View>
          )}

          {/* Messages */}
          {messages.map((message) => (
            <View
              key={message.id}
              style={[
                styles.messageBubble,
                message.type === "user"
                  ? styles.userBubble
                  : styles.sakhiBubble,
              ]}
            >
              <Text
                style={[
                  styles.messageText,
                  message.type === "sakhi" && styles.sakhiText,
                ]}
              >
                {message.text}
              </Text>
            </View>
          ))}

          {/* Live transcript while recording */}
          {voice.isRecording && (
            <View style={[styles.messageBubble, styles.userBubble, styles.liveBubble]}>
              <Text style={styles.liveText}>Listening...</Text>
            </View>
          )}

          {/* Processing indicator */}
          {voice.isProcessing && (
            <View style={styles.processingIndicator}>
              <Text style={styles.processingText}>...</Text>
            </View>
          )}

          {/* Error */}
          {voice.error && (
            <View style={styles.errorBubble}>
              <Text style={styles.errorText}>{voice.error.message}</Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputArea}>
          {/* Text Input - secondary */}
          <View style={styles.textInputContainer}>
            <TextInput
              style={styles.textInput}
              placeholder="Type instead…"
              placeholderTextColor={palette.faint}
              value={textInput}
              onChangeText={setTextInput}
              onSubmitEditing={handleTextSubmit}
              returnKeyType="send"
              multiline={false}
              editable={isAuthReady}
            />
            {textInput.length > 0 && (
              <Pressable
                style={[
                  styles.sendButton,
                  !isAuthReady && styles.sendButtonDisabled,
                ]}
                onPress={handleTextSubmit}
                disabled={!isAuthReady}
              >
                <Ionicons name="arrow-up" size={20} color={palette.fg} />
              </Pressable>
            )}
          </View>

          {/* Voice Button - primary */}
          <View style={styles.voiceButtonContainer}>
            <VoiceOrb
              state={voice.state}
              permissionState={voice.permissionState}
              onPress={handleVoiceButton}
              disabled={!isAuthReady}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// =============================================================================
// VOICE ORB
// =============================================================================

function VoiceOrb({
  state,
  permissionState,
  onPress,
  disabled,
}: {
  state: VoiceState;
  permissionState: PermissionState;
  onPress: () => void;
  disabled: boolean;
}) {
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    scaleAnim.setValue(1);
    glowAnim.setValue(0);

    if (state === "recording") {
      // Gentle pulse when recording
      Animated.loop(
        Animated.sequence([
          Animated.timing(scaleAnim, {
            toValue: 1.08,
            duration: 600,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
          Animated.timing(scaleAnim, {
            toValue: 1,
            duration: 600,
            easing: Easing.inOut(Easing.ease),
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Glow effect
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 600,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.5,
            duration: 600,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else if (state === "speaking") {
      // Subtle pulse when speaking
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 0.8,
            duration: 400,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.3,
            duration: 400,
            useNativeDriver: true,
          }),
        ])
      ).start();
    }

    return () => {
      scaleAnim.stopAnimation();
      glowAnim.stopAnimation();
    };
  }, [state, scaleAnim, glowAnim]);

  const isActive = state === "recording" || state === "processing" || state === "speaking";
  const isDenied = permissionState === "denied" || disabled;
  const orbColor = isDenied
    ? palette.muted
    : state === "recording"
      ? palette.recording
      : palette.accent;

  // Determine icon
  let iconName: "mic" | "stop" | "settings-outline" = "mic";
  if (isDenied) {
    iconName = "settings-outline";
  } else if (state === "recording") {
    iconName = "stop";
  }

  return (
    <Pressable onPress={onPress} disabled={state === "processing" || disabled}>
      <Animated.View
        style={[
          styles.orbOuter,
          {
            opacity: glowAnim.interpolate({
              inputRange: [0, 1],
              outputRange: [0, 0.3],
            }),
            backgroundColor: orbColor,
          },
        ]}
      />
      <Animated.View
        style={[
          styles.orb,
          {
            backgroundColor: isActive ? orbColor : isDenied ? palette.muted : palette.accent,
            transform: [{ scale: scaleAnim }],
          },
        ]}
      >
        <Ionicons
          name={iconName}
          size={36}
          color="#fff"
        />
      </Animated.View>
    </Pressable>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  header: {
    paddingVertical: 20,
    paddingHorizontal: 24,
    alignItems: "center",
  },
  headerTitle: {
    fontSize: 16,
    fontWeight: "500",
    color: palette.muted,
    letterSpacing: 0.5,
  },
  keyboardView: {
    flex: 1,
  },
  conversationArea: {
    flex: 1,
  },
  conversationContent: {
    padding: 24,
    paddingBottom: 20,
  },
  conversationContentEmpty: {
    flex: 1,
    justifyContent: "center",
  },

  // Empty state
  emptyState: {
    alignItems: "center",
    paddingHorizontal: 28,
  },
  primaryPrompt: {
    fontSize: 22,
    fontWeight: "400",
    color: palette.fg,
    textAlign: "center",
    lineHeight: 32,
    marginBottom: 20,
  },
  subtleHint: {
    fontSize: 14,
    color: palette.faint,
    textAlign: "center",
  },

  // Messages
  messageBubble: {
    maxWidth: "82%",
    marginBottom: 14,
    padding: 16,
    borderRadius: 20,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: palette.accent,
    borderBottomRightRadius: 6,
  },
  sakhiBubble: {
    alignSelf: "flex-start",
    backgroundColor: palette.cardBg,
    borderBottomLeftRadius: 6,
    borderWidth: 1,
    borderColor: palette.border,
  },
  messageText: {
    fontSize: 15,
    color: "#fff",
    lineHeight: 22,
  },
  sakhiText: {
    color: palette.fg,
  },
  liveBubble: {
    opacity: 0.7,
  },
  liveText: {
    fontSize: 15,
    color: "#fff",
    fontStyle: "italic",
  },
  processingIndicator: {
    alignSelf: "flex-start",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  processingText: {
    fontSize: 24,
    color: palette.muted,
    letterSpacing: 4,
  },
  errorBubble: {
    alignSelf: "center",
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    paddingVertical: 14,
    paddingHorizontal: 18,
    borderRadius: 14,
    marginTop: 12,
  },
  errorText: {
    fontSize: 14,
    color: "#ef4444",
    textAlign: "center",
    lineHeight: 20,
  },

  // Input area
  inputArea: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 32,
    alignItems: "center",
    gap: 20,
  },
  textInputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: palette.cardBg,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: palette.border,
    paddingHorizontal: 20,
    paddingVertical: 14,
    width: "100%",
    minHeight: 52,
  },
  textInput: {
    flex: 1,
    fontSize: 15,
    color: palette.fg,
    paddingVertical: 0,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: palette.accent,
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 10,
  },
  sendButtonDisabled: {
    backgroundColor: palette.subtle,
  },
  voiceButtonContainer: {
    alignItems: "center",
    marginTop: 4,
    marginBottom: 8,
  },
  orbOuter: {
    position: "absolute",
    width: 96,
    height: 96,
    borderRadius: 48,
    top: -4,
    left: -4,
  },
  orb: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: palette.accent,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 10,
  },
});

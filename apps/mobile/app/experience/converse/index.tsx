import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../../../lib/auth/AuthContext";
import { config } from "../../../lib/config";

// =============================================================================
// TYPES
// =============================================================================

interface Message {
  id: string;
  role: "user" | "sakhi";
  content: string;
  timestamp: Date;
}

// =============================================================================
// CONVERSATION SCREEN
// =============================================================================

const BACKEND_URL = config.backendUrl || "https://sakhi-production-930f.up.railway.app";

export default function ConversationScreen() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const scrollViewRef = useRef<ScrollView>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);

  const personId = user?.personId || "";

  // Scroll to bottom on new messages
  useEffect(() => {
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  // Get greeting based on time
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
  };

  const displayName = user?.fullName?.split(" ")[0] || "";

  // Send message to backend
  const sendMessage = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !personId) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsSending(true);

    // AbortController for 30s timeout (turn endpoint makes multiple LLM calls)
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);

    try {
      const url = `${BACKEND_URL}/v2/turn?user=${encodeURIComponent(personId)}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: "text" }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        if (data.reply) {
          const sakhiMessage: Message = {
            id: `sakhi-${Date.now()}`,
            role: "sakhi",
            content: data.reply,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, sakhiMessage]);
        }
      } else {
        const statusText = await res.text().catch(() => "");
        const sakhiMessage: Message = {
          id: `error-${Date.now()}`,
          role: "sakhi",
          content: `Something went wrong (${res.status}). Try again.`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, sakhiMessage]);
        console.error(`[turn] HTTP ${res.status}: ${statusText.slice(0, 200)}`);
      }
    } catch (err: unknown) {
      clearTimeout(timeout);
      const isTimeout = err instanceof Error && err.name === "AbortError";
      const errorMsg = isTimeout
        ? "That took too long. Try again — sometimes the first message is slow."
        : `Connection issue: ${err instanceof Error ? err.message : "unknown"}`;
      const sakhiMessage: Message = {
        id: `error-${Date.now()}`,
        role: "sakhi",
        content: errorMsg,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, sakhiMessage]);
      console.error("[turn] fetch error:", err);
    } finally {
      setIsSending(false);
    }
  }, [inputText, personId]);

  const handleSignOut = async () => {
    await signOut();
    router.replace("/" as never);
  };

  const hasMessages = messages.length > 0;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Text style={styles.brand}>Sakhi</Text>
          <Text style={styles.greeting}>
            {getGreeting()}
            {displayName ? `, ${displayName}` : ""}
          </Text>
        </View>
        <Pressable onPress={handleSignOut} hitSlop={12}>
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        {/* Messages */}
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesArea}
          contentContainerStyle={[
            styles.messagesContent,
            !hasMessages && styles.messagesContentEmpty,
          ]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {!hasMessages ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyPrompt}>
                This is a quiet space to unload your mind.
              </Text>
              <Text style={styles.emptyHint}>
                Say whatever is present — you don't need to sort it.
              </Text>
            </View>
          ) : (
            <>
              {messages.map((msg) => (
                <View
                  key={msg.id}
                  style={[
                    styles.bubble,
                    msg.role === "user" ? styles.userBubble : styles.sakhiBubble,
                  ]}
                >
                  <Text
                    style={[
                      styles.bubbleText,
                      msg.role === "sakhi" && styles.sakhiBubbleText,
                    ]}
                  >
                    {msg.content}
                  </Text>
                </View>
              ))}
              {isSending && (
                <View style={[styles.bubble, styles.sakhiBubble, { opacity: 0.6 }]}>
                  <ActivityIndicator size="small" color="#a1a1aa" />
                </View>
              )}
            </>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputArea}>
          <View style={styles.inputRow}>
            <TextInput
              style={styles.textInput}
              placeholder="What's on your mind?"
              placeholderTextColor="#3f3f46"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={sendMessage}
              returnKeyType="send"
              multiline={false}
              editable={!isSending}
            />
            {inputText.trim().length > 0 && (
              <Pressable
                style={[styles.sendButton, isSending && { opacity: 0.5 }]}
                onPress={sendMessage}
                disabled={isSending}
              >
                <Ionicons name="arrow-up" size={20} color="#ffffff" />
              </Pressable>
            )}
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const palette = {
  bg: "#0a0a0a",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  subtle: "#52525b",
  faint: "#3f3f46",
  accent: "#6366f1",
  cardBg: "#141416",
  border: "#1f1f23",
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: palette.bg,
  },
  keyboardView: {
    flex: 1,
  },

  // Header
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderBottomWidth: 1,
    borderBottomColor: palette.border,
  },
  headerLeft: {},
  brand: {
    fontSize: 13,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    color: palette.muted,
    marginBottom: 4,
  },
  greeting: {
    fontSize: 18,
    fontWeight: "500",
    color: palette.fg,
  },
  signOutText: {
    fontSize: 12,
    color: palette.subtle,
    marginTop: 4,
  },

  // Messages
  messagesArea: {
    flex: 1,
  },
  messagesContent: {
    padding: 24,
    paddingBottom: 8,
  },
  messagesContentEmpty: {
    flex: 1,
    justifyContent: "center",
  },

  // Empty state
  emptyState: {
    alignItems: "center",
    paddingHorizontal: 28,
  },
  emptyPrompt: {
    fontSize: 22,
    fontWeight: "400",
    color: palette.fg,
    textAlign: "center",
    lineHeight: 32,
    marginBottom: 20,
  },
  emptyHint: {
    fontSize: 14,
    color: palette.faint,
    textAlign: "center",
  },

  // Bubbles
  bubble: {
    maxWidth: "82%",
    marginBottom: 14,
    paddingVertical: 14,
    paddingHorizontal: 18,
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
  bubbleText: {
    fontSize: 15,
    color: "#ffffff",
    lineHeight: 22,
  },
  sakhiBubbleText: {
    color: palette.fg,
  },

  // Input
  inputArea: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: palette.border,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: palette.cardBg,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: palette.border,
    paddingHorizontal: 18,
    paddingVertical: 12,
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
});

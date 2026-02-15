import React, { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Modal,
  Dimensions,
  ScrollView,
  NativeSyntheticEvent,
  NativeScrollEvent,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "../lib/auth/AuthContext";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

// =============================================================================
// INTRO CARDS DATA
// =============================================================================

const INTRO_CARDS = [
  {
    id: 1,
    title: "Clarity is your natural state.",
    body: "But friction builds.\nInside you, and around you.",
    accent: "The way your body feels, your thoughts, emotions, decisions, and distractions.",
  },
  {
    id: 2,
    title: "Sakhi helps you see and release friction.",
    body: "Within you: the patterns clouding your clarity.\n\nAround you: the tasks and decisions pulling at your attention.",
    accent: "Less friction. More you.",
  },
  {
    id: 3,
    title: "Just talk.",
    body: "About your day. Or a decision. Or something you want off your plate.\n\nThink out loud.\n\nOr tell me what you don't want to deal with.",
    accent: "You'll start to feel the difference.",
  },
];

// =============================================================================
// HOME SCREEN
// =============================================================================

export default function Index() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [showIntro, setShowIntro] = useState(false);
  const [currentCard, setCurrentCard] = useState(0);
  const scrollRef = useRef<ScrollView>(null);

  // Auto-redirect returning users to the main app
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace("/experience/converse" as never);
    }
  }, [isLoading, isAuthenticated, router]);

  const handleScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const offsetX = event.nativeEvent.contentOffset.x;
    const index = Math.round(offsetX / SCREEN_WIDTH);
    setCurrentCard(index);
  };

  const handleCloseIntro = () => {
    setShowIntro(false);
    setCurrentCard(0);
  };

  const isLastCard = currentCard === INTRO_CARDS.length - 1;

  // Show loading while checking auth state
  if (isLoading || isAuthenticated) {
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="light-content" />
        <View style={styles.content}>
          <ActivityIndicator size="large" color="#6366f1" />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      <View style={styles.content}>
        {/* Centered text */}
        <View style={styles.textContainer}>
          <Text style={styles.headline}>
            This is a quiet space to unload your mind.
          </Text>
          <Text style={styles.subheadline}>
            You can talk, or hand something off.
          </Text>
        </View>

        {/* BEGIN button */}
        <Pressable
          style={styles.beginButton}
          onPress={() => router.push("/auth" as never)}
        >
          <Text style={styles.beginText}>BEGIN</Text>
        </Pressable>

        {/* What is Sakhi link */}
        <Pressable
          style={styles.learnMoreButton}
          onPress={() => setShowIntro(true)}
        >
          <Text style={styles.learnMoreText}>What is Sakhi?</Text>
        </Pressable>
      </View>

      {/* Intro Modal */}
      <Modal
        visible={showIntro}
        animationType="fade"
        transparent={true}
        onRequestClose={handleCloseIntro}
      >
        <View style={styles.modalOverlay}>
          <SafeAreaView style={styles.modalContainer}>
            {/* Close button */}
            <Pressable style={styles.closeButton} onPress={handleCloseIntro}>
              <Text style={styles.closeButtonText}>✕</Text>
            </Pressable>

            {/* Swipeable cards */}
            <ScrollView
              ref={scrollRef}
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onScroll={handleScroll}
              scrollEventThrottle={16}
              style={styles.cardsScrollView}
            >
              {INTRO_CARDS.map((card) => (
                <View key={card.id} style={styles.cardContainer}>
                  <View style={styles.card}>
                    <Text style={styles.cardTitle}>{card.title}</Text>
                    <Text style={styles.cardBody}>{card.body}</Text>
                    <Text style={styles.cardAccent}>{card.accent}</Text>
                  </View>
                </View>
              ))}
            </ScrollView>

            {/* Pagination dots */}
            <View style={styles.pagination}>
              {INTRO_CARDS.map((_, index) => (
                <View
                  key={index}
                  style={[
                    styles.paginationDot,
                    currentCard === index && styles.paginationDotActive,
                  ]}
                />
              ))}
            </View>

            {/* Reassurance text - only on last card */}
            {isLastCard && (
              <Text style={styles.reassurance}>We'll start small.</Text>
            )}

            {/* Got it button - only enabled on last card */}
            <Pressable
              style={[
                styles.gotItButton,
                !isLastCard && styles.gotItButtonDisabled,
              ]}
              onPress={handleCloseIntro}
              disabled={!isLastCard}
            >
              <Text
                style={[
                  styles.gotItText,
                  !isLastCard && styles.gotItTextDisabled,
                ]}
              >
                {isLastCard ? "Got it" : "Swipe to continue"}
              </Text>
            </Pressable>
          </SafeAreaView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// =============================================================================
// STYLES
// =============================================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0a",
  },
  content: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 40,
  },
  textContainer: {
    alignItems: "center",
    marginBottom: 56,
  },
  headline: {
    fontSize: 24,
    fontWeight: "400",
    color: "#ffffff",
    textAlign: "center",
    lineHeight: 34,
    marginBottom: 20,
  },
  subheadline: {
    fontSize: 16,
    fontWeight: "400",
    color: "#71717a",
    textAlign: "center",
    lineHeight: 24,
  },
  beginButton: {
    paddingVertical: 16,
    paddingHorizontal: 32,
    marginBottom: 32,
    minHeight: 48,
    justifyContent: "center",
  },
  beginText: {
    fontSize: 14,
    fontWeight: "500",
    color: "#71717a",
    letterSpacing: 2,
  },
  learnMoreButton: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    minHeight: 44,
    justifyContent: "center",
  },
  learnMoreText: {
    fontSize: 13,
    color: "#6366f1",
    textDecorationLine: "underline",
  },

  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.96)",
  },
  modalContainer: {
    flex: 1,
    justifyContent: "center",
  },
  closeButton: {
    position: "absolute",
    top: 56,
    right: 16,
    zIndex: 10,
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  closeButtonText: {
    fontSize: 20,
    color: "#52525b",
  },
  cardsScrollView: {
    flexGrow: 0,
  },
  cardContainer: {
    width: SCREEN_WIDTH,
    paddingHorizontal: 36,
    justifyContent: "center",
  },
  card: {
    alignItems: "center",
    paddingVertical: 48,
  },
  cardTitle: {
    fontSize: 26,
    fontWeight: "500",
    color: "#ffffff",
    textAlign: "center",
    lineHeight: 36,
    marginBottom: 28,
    letterSpacing: -0.5,
  },
  cardBody: {
    fontSize: 16,
    color: "#a1a1aa",
    textAlign: "center",
    lineHeight: 26,
    marginBottom: 36,
  },
  cardAccent: {
    fontSize: 14,
    color: "#6366f1",
    textAlign: "center",
    fontStyle: "italic",
    lineHeight: 22,
  },
  pagination: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 10,
    marginTop: 40,
    marginBottom: 32,
  },
  paginationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#27272a",
  },
  paginationDotActive: {
    backgroundColor: "#6366f1",
    width: 28,
  },
  reassurance: {
    fontSize: 13,
    color: "#52525b",
    textAlign: "center",
    marginBottom: 20,
  },
  gotItButton: {
    marginHorizontal: 28,
    backgroundColor: "#18191d",
    paddingVertical: 18,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#27272a",
    minHeight: 56,
    justifyContent: "center",
  },
  gotItButtonDisabled: {
    backgroundColor: "transparent",
    borderColor: "transparent",
  },
  gotItText: {
    fontSize: 15,
    fontWeight: "500",
    color: "#f4f4f5",
  },
  gotItTextDisabled: {
    color: "#52525b",
    fontSize: 13,
  },
});

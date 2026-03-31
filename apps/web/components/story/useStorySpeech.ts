"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Web Speech API wrapper for story narration.
 * Utterances are queued (not cancelled) so each line plays through before the
 * next begins. Mutable ref is safe to use inside GSAP callbacks without
 * re-creating the timeline.
 *
 * Chrome blocks speechSynthesis until a user gesture. Call prime() on the
 * first interaction to unblock it.
 */
export function useStorySpeech() {
  const [muted, setMuted] = useState(false);
  const mutedRef = useRef(false);
  const primedRef = useRef(false);
  const readyRef = useRef(false);
  const queueRef = useRef<string[]>([]);

  // Eagerly warm up voice list — browsers load voices async on first call
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.speechSynthesis.getVoices();
    const onVoicesChanged = () => window.speechSynthesis.getVoices();
    window.speechSynthesis.addEventListener("voiceschanged", onVoicesChanged);
    return () =>
      window.speechSynthesis.removeEventListener("voiceschanged", onVoicesChanged);
  }, []);

  const getPreferredVoice = useCallback(() => {
    if (typeof window === "undefined") {
      return null;
    }

    const voices = window.speechSynthesis.getVoices();
    return (
      voices.find((v) => v.lang === "en-US" && /Google|Samantha|Alex/.test(v.name)) ??
      voices.find((v) => v.lang === "en-US") ??
      voices.find((v) => v.lang.startsWith("en")) ??
      null
    );
  }, []);

  const speakNow = useCallback((text: string) => {
    if (mutedRef.current || typeof window === "undefined" || !text.trim()) return;

    window.speechSynthesis.resume();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.88;
    utterance.pitch = 1.0;

    const preferred = getPreferredVoice();
    if (preferred) {
      utterance.voice = preferred;
    }

    window.speechSynthesis.speak(utterance);
  }, [getPreferredVoice]);

  const flushQueue = useCallback(() => {
    if (!readyRef.current || mutedRef.current || typeof window === "undefined") {
      return;
    }

    window.speechSynthesis.resume();

    while (queueRef.current.length > 0) {
      const next = queueRef.current.shift();
      if (next) {
        speakNow(next);
      }
    }
  }, [speakNow]);

  // Chrome requires a user gesture before speech synthesis works.
  // Call this on the first mouse/touch event.
  const prime = useCallback(() => {
    if (primedRef.current || typeof window === "undefined") return;
    primedRef.current = true;

    // Speak a silent utterance, allow the event loop to tick, then mark the
    // synthesizer as ready and flush any queued narration.
    const wake = new SpeechSynthesisUtterance(" ");
    wake.volume = 0;
    wake.rate = 1;
    wake.pitch = 1;
    wake.onend = () => {
      readyRef.current = true;
      flushQueue();
    };
    wake.onerror = () => {
      readyRef.current = true;
      flushQueue();
    };

    window.speechSynthesis.resume();
    window.speechSynthesis.speak(wake);
    window.setTimeout(() => {
      readyRef.current = true;
      window.speechSynthesis.cancel();
      flushQueue();
    }, 40);
  }, [flushQueue]);

  const speak = useCallback((text: string) => {
    if (mutedRef.current || typeof window === "undefined" || !text.trim()) return;

    if (!readyRef.current) {
      queueRef.current.push(text);
      return;
    }

    speakNow(text);
  }, [speakNow]);

  const stop = useCallback(() => {
    queueRef.current = [];
    if (typeof window !== "undefined") window.speechSynthesis.cancel();
  }, []);

  const toggleMute = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      mutedRef.current = next;
      if (next && typeof window !== "undefined") {
        queueRef.current = [];
        window.speechSynthesis.cancel();
      } else if (!next) {
        flushQueue();
      }
      return next;
    });
  }, [flushQueue]);

  // Expose a stable ref so GSAP callbacks can call speak() without
  // needing the timeline to be re-created when mute state changes.
  const speakRef = useRef<((text: string) => void) | null>(null);
  speakRef.current = speak;

  return { speak, stop, prime, muted, toggleMute, speakRef };
}

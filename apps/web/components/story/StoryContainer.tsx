"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import Scene1Chaos from "@/components/story/Scene1Chaos";
import Scene2Breakdown from "@/components/story/Scene2Breakdown";
import Scene3Reveal from "@/components/story/Scene3Reveal";
import Scene4Continuity from "@/components/story/Scene4Continuity";
// import Scene4bHealthArc from "@/components/story/Scene4bHealthArc";
import Scene5Email from "@/components/story/Scene5Email";
import Scene6Vision from "@/components/story/Scene6Vision";
import { useStoryTimeline } from "@/components/story/useStoryTimeline";

const AUDIO_SRC = "/audio/sakhi-ambient.mp3";
const FADE_DURATION = 1200; // ms
const TARGET_VOLUME = 0.45;

function PlayIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-current">
      <path d="M8 6.5v11l9-5.5-9-5.5Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-current">
      <path d="M7.5 6.5h3v11h-3zM13.5 6.5h3v11h-3z" />
    </svg>
  );
}

function RestartIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-4 w-4 fill-none stroke-current"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 12a8 8 0 1 1-2.34-5.66" />
      <path d="M20 4v5h-5" />
    </svg>
  );
}

function FullscreenEnterIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function FullscreenExitIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
    </svg>
  );
}

function MuteIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 5 6 9H2v6h4l5 4V5Z" />
      <line x1="23" y1="9" x2="17" y2="15" />
      <line x1="17" y1="9" x2="23" y2="15" />
    </svg>
  );
}

function UnmuteIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 5 6 9H2v6h4l5 4V5Z" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    </svg>
  );
}

export default function StoryContainer({ autoPlay: _autoPlay = false }: { autoPlay?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hideControlsTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [controlsVisible, setControlsVisible] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [started, setStarted] = useState(false);

  const { isPaused, isComplete, progress, duration, togglePlayback, restart, seekTo } =
    useStoryTimeline(containerRef);

  // ── Audio ────────────────────────────────────────────────────────────────
  const audioRef = useRef<HTMLAudioElement>(null);
  const fadeRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isMuted, setIsMuted] = useState(false);

  const fadeVolume = useCallback((targetVol: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    if (fadeRef.current) clearInterval(fadeRef.current);
    const steps = 30;
    const stepMs = FADE_DURATION / steps;
    const start = audio.volume;
    const delta = (targetVol - start) / steps;
    let count = 0;
    fadeRef.current = setInterval(() => {
      count++;
      audio.volume = Math.min(1, Math.max(0, start + delta * count));
      if (count >= steps) {
        if (fadeRef.current) clearInterval(fadeRef.current);
        if (targetVol === 0) audio.pause();
      }
    }, stepMs);
  }, []);

  // Sync play/pause with story
  useEffect(() => {
    if (!started) return;
    const audio = audioRef.current;
    if (!audio) return;
    if (!isPaused && !isComplete) {
      if (!isMuted) {
        audio.play().catch(() => {});
        fadeVolume(TARGET_VOLUME);
      }
    } else {
      fadeVolume(0);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPaused, isComplete, started]);

  const toggleMute = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isMuted) {
      audio.volume = 0;
      audio.play().catch(() => {});
      fadeVolume(TARGET_VOLUME);
      setIsMuted(false);
    } else {
      fadeVolume(0);
      setIsMuted(true);
    }
  }, [isMuted, fadeVolume]);

  // Start everything: audio + story
  const handleStart = useCallback((withSound: boolean) => {
    const audio = audioRef.current;
    setIsMuted(!withSound);
    setStarted(true);
    if (audio && withSound) {
      audio.volume = 0;
      audio.play().catch(() => {});
      fadeVolume(TARGET_VOLUME);
    }
    togglePlayback();
  }, [togglePlayback, fadeVolume]);

  const handleTogglePlayback = useCallback(() => {
    togglePlayback();
  }, [togglePlayback]);

  useEffect(() => {
    return () => {
      if (fadeRef.current) clearInterval(fadeRef.current);
    };
  }, []);

  const elapsed = Math.round(progress * duration);
  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  const revealControls = useCallback(() => {
    setControlsVisible(true);
    if (hideControlsTimeoutRef.current) clearTimeout(hideControlsTimeoutRef.current);
    hideControlsTimeoutRef.current = setTimeout(() => setControlsVisible(false), 1800);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  }, []);

  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  useEffect(() => {
    return () => {
      if (hideControlsTimeoutRef.current) clearTimeout(hideControlsTimeoutRef.current);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative h-screen w-screen overflow-hidden bg-gradient-to-br from-[#020617] via-[#020617] to-[#0b1220] text-white"
      onMouseMove={revealControls}
      onMouseEnter={revealControls}
      onMouseLeave={() => {
        if (hideControlsTimeoutRef.current) clearTimeout(hideControlsTimeoutRef.current);
        setControlsVisible(false);
      }}
    >
      {/* Background audio */}
      <audio ref={audioRef} src={AUDIO_SRC} loop preload="auto" />

      {/* Start screen overlay */}
      {!started && (
        <div className="absolute inset-0 z-[200] flex flex-col items-center justify-center bg-[#020617]">
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.35em] text-[#8ab0ff]/50">Sakhi</p>
          <h1 className="mb-2 text-center text-[clamp(1.4rem,2.5vw,2rem)] font-bold tracking-[-0.04em] text-white">
            The continuity layer for the human mind.
          </h1>
          <p className="mb-10 text-[0.82rem] text-slate-500">Best experienced with sound.</p>

          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => handleStart(true)}
              className="flex items-center gap-2.5 rounded-full bg-[#8cb7ff]/10 border border-[#8cb7ff]/25 px-6 py-3 text-[0.85rem] font-semibold text-[#8cb7ff] transition hover:bg-[#8cb7ff]/20 hover:border-[#8cb7ff]/40"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current shrink-0"><path d="M8 6.5v11l9-5.5-9-5.5Z" /></svg>
              Play with sound
            </button>
            <button
              type="button"
              onClick={() => handleStart(false)}
              className="text-[0.78rem] text-slate-500 transition hover:text-slate-300 underline underline-offset-4"
            >
              Play without sound
            </button>
          </div>
        </div>
      )}

      {/* Mute / unmute button — top-right, visible after start */}
      {started && (
        <button
          type="button"
          onClick={toggleMute}
          aria-label={isMuted ? "Unmute music" : "Mute music"}
          className="absolute right-5 top-5 z-[130] flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-white/40 backdrop-blur-sm transition hover:border-white/20 hover:text-white/70 sm:right-6 sm:top-6"
        >
          {isMuted ? <MuteIcon /> : <UnmuteIcon />}
        </button>
      )}

      <div
        className={`absolute inset-x-0 bottom-5 z-[120] px-4 transition-all duration-300 sm:bottom-7 sm:px-6 ${
          controlsVisible && started
            ? "translate-y-0 opacity-100"
            : "translate-y-3 opacity-0 pointer-events-none"
        }`}
      >
        <div className="mx-auto flex w-full max-w-4xl items-center gap-3 rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(8,11,20,0.82),rgba(4,7,14,0.92))] px-3 py-3 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:gap-4 sm:px-4">
          <button
            type="button"
            onClick={handleTogglePlayback}
            onFocus={revealControls}
            aria-label={isComplete ? "Play story again" : isPaused ? "Play story" : "Pause story"}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/12 bg-white/6 text-slate-100 transition hover:bg-white/10"
          >
            {isComplete || isPaused ? <PlayIcon /> : <PauseIcon />}
          </button>
          <button
            type="button"
            onClick={() => { restart(); }}
            onFocus={revealControls}
            aria-label="Restart story"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-transparent text-slate-300 transition hover:border-white/18 hover:text-white"
          >
            <RestartIcon />
          </button>
          <input
            type="range"
            min={0}
            max={1000}
            step={1}
            value={Math.round(progress * 1000)}
            onInput={(event) => {
              seekTo(Number(event.currentTarget.value) / 1000);
            }}
            onChange={(event) => {
              seekTo(Number(event.currentTarget.value) / 1000);
            }}
            onFocus={revealControls}
            aria-label="Story timeline"
            className="h-1 w-full cursor-pointer appearance-none rounded-full bg-white/15 accent-[#c7d3ff]"
          />
          <div className="flex min-w-[5.5rem] items-center justify-end gap-1 text-[10px] font-semibold tabular-nums tracking-[0.1em] text-slate-300">
            <span>{fmt(elapsed)}</span>
            <span className="text-slate-500">/</span>
            <span className="text-slate-500">{fmt(Math.round(duration))}</span>
          </div>
          <button
            type="button"
            onClick={toggleFullscreen}
            onFocus={revealControls}
            aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 bg-transparent text-slate-300 transition hover:border-white/18 hover:text-white"
          >
            {isFullscreen ? <FullscreenExitIcon /> : <FullscreenEnterIcon />}
          </button>
        </div>
      </div>

      <div id="scene-1" className="scene absolute inset-0 z-10">
        <Scene1Chaos />
      </div>
      <div id="scene-2" className="scene absolute inset-0 z-20 opacity-0">
        <Scene2Breakdown />
      </div>
      <div id="scene-3" className="scene absolute inset-0 z-30 opacity-0">
        <Scene3Reveal />
      </div>
      <div id="scene-4" className="scene absolute inset-0 z-40 opacity-0">
        <Scene4Continuity />
      </div>
      {/* Health arc — parked, uncomment to restore
      <div id="scene-4b" className="scene absolute inset-0 z-[45] opacity-0">
        <Scene4bHealthArc />
      </div>
      */}
      <div id="scene-5" className="scene absolute inset-0 z-50 opacity-0">
        <Scene5Email />
      </div>
      <div id="scene-6" className="scene absolute inset-0 z-[60] opacity-0">
        <Scene6Vision />
      </div>
    </div>
  );
}

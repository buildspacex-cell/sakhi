"use client";

import { useEffect, useState, useRef } from "react";

/**
 * MeshConnection - Animated visual for Sakhi-to-Sakhi communication
 *
 * Shows data packets flowing between two Sakhis with:
 * - Animated connection line with gradient
 * - Floating data packets
 * - Pulsing center node
 * - Different visual states
 */

export type ConnectionState =
  | "idle"
  | "connecting"
  | "active"
  | "coordinating"
  | "confirmed"
  | "complete";

interface MeshConnectionProps {
  state: ConnectionState;
  leftLabel?: string;
  rightLabel?: string;
  statusText?: string;
}

const palette = {
  bg: "#0e0f12",
  accent: "#6366f1",
  accentLight: "#818cf8",
  accentDim: "rgba(99, 102, 241, 0.2)",
  success: "#22c55e",
  successDim: "rgba(34, 197, 94, 0.2)",
  muted: "#71717a",
  warning: "#f59e0b",
};

export function MeshConnection({
  state,
  leftLabel = "Your Sakhi",
  rightLabel = "Mom's Sakhi",
  statusText,
}: MeshConnectionProps) {
  const [packets, setPackets] = useState<{ id: number; direction: "left" | "right"; progress: number }[]>([]);
  const [particles, setParticles] = useState<{ id: number; x: number; y: number; opacity: number }[]>([]);
  const packetIdRef = useRef(0);
  const particleIdRef = useRef(0);

  const isActive = state !== "idle";
  const isConnecting = state === "connecting";
  const isCoordinating = state === "coordinating" || state === "active";
  const isConfirmed = state === "confirmed" || state === "complete";

  // Spawn packets when coordinating
  useEffect(() => {
    if (!isCoordinating) {
      setPackets([]);
      return;
    }

    const interval = setInterval(() => {
      const direction: "left" | "right" = Math.random() > 0.5 ? "left" : "right";
      const newPacket = {
        id: packetIdRef.current++,
        direction,
        progress: 0,
      };
      setPackets(prev => [...prev.slice(-6), newPacket]);
    }, 600);

    return () => clearInterval(interval);
  }, [isCoordinating]);

  // Animate packets
  useEffect(() => {
    if (packets.length === 0) return;

    const interval = setInterval(() => {
      setPackets(prev =>
        prev
          .map(p => ({ ...p, progress: p.progress + 0.05 }))
          .filter(p => p.progress <= 1)
      );
    }, 30);

    return () => clearInterval(interval);
  }, [packets.length]);

  // Spawn particles on confirmed
  useEffect(() => {
    if (!isConfirmed) {
      setParticles([]);
      return;
    }

    // Initial burst
    const burst = Array.from({ length: 12 }, (_, i) => ({
      id: particleIdRef.current++,
      x: 50 + (Math.random() - 0.5) * 40,
      y: 50 + (Math.random() - 0.5) * 40,
      opacity: 1,
    }));
    setParticles(burst);

    // Fade out
    const fadeInterval = setInterval(() => {
      setParticles(prev =>
        prev
          .map(p => ({ ...p, opacity: p.opacity - 0.02, y: p.y - 0.5 }))
          .filter(p => p.opacity > 0)
      );
    }, 50);

    return () => clearInterval(fadeInterval);
  }, [isConfirmed]);

  // Determine colors based on state
  const lineColor = isConfirmed ? palette.success : palette.accent;
  const glowColor = isConfirmed ? palette.successDim : palette.accentDim;
  const centerIcon = isConfirmed ? "✓" : isCoordinating ? "⟷" : isConnecting ? "•••" : "○";

  return (
    <div style={styles.container}>
      {/* CSS Keyframes */}
      <style>{`
        @keyframes meshPulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.15); opacity: 0.8; }
        }
        @keyframes meshGlow {
          0%, 100% { box-shadow: 0 0 20px ${glowColor}, 0 0 40px ${glowColor}; }
          50% { box-shadow: 0 0 30px ${glowColor}, 0 0 60px ${glowColor}; }
        }
        @keyframes meshLineFlow {
          0% { background-position: 0% 50%; }
          100% { background-position: 200% 50%; }
        }
        @keyframes meshConnecting {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
        @keyframes meshParticleFloat {
          0% { transform: translateY(0) scale(1); }
          100% { transform: translateY(-20px) scale(0); }
        }
        @keyframes meshPacketGlow {
          0%, 100% { filter: drop-shadow(0 0 4px ${lineColor}); }
          50% { filter: drop-shadow(0 0 8px ${lineColor}); }
        }
      `}</style>

      {/* Connection Line */}
      <svg
        viewBox="0 0 200 100"
        style={styles.svg}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Definitions */}
        <defs>
          {/* Gradient for line */}
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={lineColor} stopOpacity={isActive ? 0.8 : 0.2} />
            <stop offset="50%" stopColor={lineColor} stopOpacity={isActive ? 1 : 0.3} />
            <stop offset="100%" stopColor={lineColor} stopOpacity={isActive ? 0.8 : 0.2} />
          </linearGradient>

          {/* Animated flow gradient */}
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="40%" stopColor={lineColor} />
            <stop offset="60%" stopColor={lineColor} />
            <stop offset="100%" stopColor="transparent" />
            <animate
              attributeName="x1"
              values="-100%;100%"
              dur="1.5s"
              repeatCount="indefinite"
            />
            <animate
              attributeName="x2"
              values="0%;200%"
              dur="1.5s"
              repeatCount="indefinite"
            />
          </linearGradient>

          {/* Glow filter */}
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Packet gradient */}
          <radialGradient id="packetGradient">
            <stop offset="0%" stopColor={lineColor} stopOpacity="1" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0.5" />
          </radialGradient>
        </defs>

        {/* Background line (always visible, dimmed when idle) */}
        <path
          d="M 20 50 Q 100 50 180 50"
          fill="none"
          stroke={palette.muted}
          strokeWidth="1"
          strokeDasharray={isConnecting ? "4 4" : "none"}
          opacity={isActive ? 0.3 : 0.15}
          style={isConnecting ? { animation: "meshConnecting 1s infinite" } : undefined}
        />

        {/* Active connection line */}
        {isActive && (
          <path
            d="M 20 50 Q 100 50 180 50"
            fill="none"
            stroke="url(#lineGradient)"
            strokeWidth="2"
            filter="url(#glow)"
          />
        )}

        {/* Flow animation line */}
        {isCoordinating && (
          <path
            d="M 20 50 Q 100 50 180 50"
            fill="none"
            stroke="url(#flowGradient)"
            strokeWidth="3"
            filter="url(#glow)"
          />
        )}

        {/* Data Packets */}
        {packets.map(packet => {
          const x = packet.direction === "right"
            ? 20 + (160 * packet.progress)
            : 180 - (160 * packet.progress);
          return (
            <g key={packet.id} style={{ animation: "meshPacketGlow 0.5s infinite" }}>
              <circle
                cx={x}
                cy={50}
                r={4}
                fill="url(#packetGradient)"
                filter="url(#glow)"
              />
              {/* Packet trail */}
              <circle
                cx={x - (packet.direction === "right" ? 8 : -8)}
                cy={50}
                r={2}
                fill={lineColor}
                opacity={0.5}
              />
            </g>
          );
        })}

        {/* Left endpoint */}
        <circle
          cx={20}
          cy={50}
          r={8}
          fill={isActive ? glowColor : "rgba(113, 113, 122, 0.2)"}
          stroke={isActive ? lineColor : palette.muted}
          strokeWidth={2}
        />

        {/* Right endpoint */}
        <circle
          cx={180}
          cy={50}
          r={8}
          fill={isActive ? glowColor : "rgba(113, 113, 122, 0.2)"}
          stroke={isActive ? lineColor : palette.muted}
          strokeWidth={2}
        />

        {/* Center node */}
        <g style={isActive ? { animation: "meshPulse 2s infinite" } : undefined}>
          <circle
            cx={100}
            cy={50}
            r={isConfirmed ? 16 : 14}
            fill={glowColor}
            stroke={lineColor}
            strokeWidth={2}
            style={isActive ? { animation: "meshGlow 2s infinite" } : undefined}
          />
          <text
            x={100}
            y={50}
            textAnchor="middle"
            dominantBaseline="central"
            fill={lineColor}
            fontSize={isConfirmed ? 14 : 10}
            fontWeight="bold"
          >
            {centerIcon}
          </text>
        </g>

        {/* Confirmation particles */}
        {particles.map(particle => (
          <circle
            key={particle.id}
            cx={particle.x * 2}
            cy={particle.y}
            r={3}
            fill={palette.success}
            opacity={particle.opacity}
          />
        ))}
      </svg>

      {/* Labels */}
      <div style={styles.labels}>
        <span style={{ ...styles.label, color: isActive ? lineColor : palette.muted }}>
          {leftLabel}
        </span>
        <span style={styles.statusText}>
          {statusText || getDefaultStatusText(state)}
        </span>
        <span style={{ ...styles.label, color: isActive ? lineColor : palette.muted }}>
          {rightLabel}
        </span>
      </div>
    </div>
  );
}

function getDefaultStatusText(state: ConnectionState): string {
  switch (state) {
    case "idle": return "Ready to connect";
    case "connecting": return "Establishing connection...";
    case "active": return "Connected";
    case "coordinating": return "Coordinating...";
    case "confirmed": return "Confirmed!";
    case "complete": return "Complete";
    default: return "";
  }
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "20px 0",
    minWidth: 180,
  },
  svg: {
    width: "100%",
    maxWidth: 200,
    height: 100,
  },
  labels: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    width: "100%",
    maxWidth: 200,
    marginTop: 8,
    gap: 8,
  },
  label: {
    fontSize: 10,
    fontWeight: 500,
    textAlign: "center",
    flex: 1,
  },
  statusText: {
    fontSize: 11,
    color: palette.muted,
    textAlign: "center",
    flex: 2,
    whiteSpace: "nowrap",
  },
};

export default MeshConnection;

"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";

export const dynamic = "force-dynamic";

// =============================================================================
// TYPES
// =============================================================================

interface AuthUser {
  person_id: string;
  email: string;
  full_name: string | null;
}

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  event_type: string;
  energy_required?: string;
}

interface Relationship {
  name: string;
  relationship_type: string;
  closeness: number;
  days_since_contact?: number;
  frequency_target?: string;
}

interface FrictionState {
  operating_system?: string;
  friction_state?: string;
  friction_name?: string;
  drift_percentage?: number;
  current_state?: { vata: number; pitta: number; kapha: number };
  description?: string;
  severity?: string;
}

interface DashboardData {
  today: {
    date: string;
    greeting: string;
    events: CalendarEvent[];
    event_count: number;
  };
  energy: FrictionState | null;
  relationships: {
    needing_attention: Relationship[];
    total_count: number;
  };
  upcoming: {
    events: CalendarEvent[];
  };
}

interface WidgetConfig {
  id: string;
  visible: boolean;
  order: number;
}

// =============================================================================
// PALETTE
// =============================================================================

const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  success: "#22c55e",
  warning: "#f59e0b",
  error: "#ef4444",
  // Friction states
  chaos: "#e8c547",
  intensity: "#ef6461",
  stagnation: "#4787e8",
  balanced: "#22c55e",
};

// =============================================================================
// ICONS
// =============================================================================

const IconCalendar = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconUsers = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const IconZap = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const IconSun = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
);

const IconSettings = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

const IconMic = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);

const IconMessageCircle = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
  </svg>
);

const IconClock = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function DashboardPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <DashboardContent />
    </Suspense>
  );
}

function LoadingState() {
  return (
    <div style={{
      minHeight: "100vh",
      background: palette.bg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: palette.muted,
    }}>
      Loading...
    </div>
  );
}

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [widgetConfig, setWidgetConfig] = useState<WidgetConfig[]>([
    { id: "today", visible: true, order: 0 },
    { id: "energy", visible: true, order: 1 },
    { id: "relationships", visible: true, order: 2 },
    { id: "calendar", visible: true, order: 3 },
  ]);

  // Load user and widget config
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
          const userData = await res.json();
          setAuthUser(userData);
        }
      } catch (err) {
        console.error("Error fetching user:", err);
      }
    };

    // Load widget config from localStorage
    const savedConfig = localStorage.getItem("sakhi_dashboard_config");
    if (savedConfig) {
      try {
        setWidgetConfig(JSON.parse(savedConfig));
      } catch {
        // Use default
      }
    }

    fetchUser();
  }, []);

  // Fetch dashboard data
  useEffect(() => {
    const personId = authUser?.person_id || searchParams?.get("user");
    if (!personId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        // Fetch all data in parallel
        const [todayRes, frictionRes, relationshipsRes, upcomingRes] = await Promise.all([
          fetch(`/api/calendar/${personId}/today`).catch(() => null),
          fetch(`/api/friction/state/friction/${personId}`).catch(() => null),
          fetch(`/api/relationships/${personId}/needing-attention?limit=3`).catch(() => null),
          fetch(`/api/calendar/${personId}/events?limit=5`).catch(() => null),
        ]);

        const today = todayRes?.ok ? await todayRes.json() : null;
        const friction = frictionRes?.ok ? await frictionRes.json() : null;
        const relationships = relationshipsRes?.ok ? await relationshipsRes.json() : null;
        const upcoming = upcomingRes?.ok ? await upcomingRes.json() : null;

        // Build greeting
        const hour = new Date().getHours();
        let greeting = "Good morning";
        if (hour >= 12 && hour < 17) greeting = "Good afternoon";
        else if (hour >= 17) greeting = "Good evening";

        const firstName = authUser?.full_name?.split(" ")[0];
        if (firstName) greeting = `${greeting}, ${firstName}`;

        setData({
          today: {
            date: today?.date || new Date().toISOString().split("T")[0],
            greeting,
            events: today?.events || [],
            event_count: today?.count || 0,
          },
          energy: friction?.status === "ok" ? friction : null,
          relationships: {
            needing_attention: relationships?.relationships || [],
            total_count: relationships?.relationships?.length || 0,
          },
          upcoming: {
            events: upcoming?.events || [],
          },
        });
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [authUser, searchParams]);

  // Save widget config
  const saveWidgetConfig = useCallback((config: WidgetConfig[]) => {
    setWidgetConfig(config);
    localStorage.setItem("sakhi_dashboard_config", JSON.stringify(config));
  }, []);

  const toggleWidget = useCallback((id: string) => {
    const newConfig = widgetConfig.map((w) =>
      w.id === id ? { ...w, visible: !w.visible } : w
    );
    saveWidgetConfig(newConfig);
  }, [widgetConfig, saveWidgetConfig]);

  const personId = authUser?.person_id || searchParams?.get("user") || "";

  if (loading) {
    return <LoadingState />;
  }

  // Sort widgets by order
  const sortedWidgets = [...widgetConfig].sort((a, b) => a.order - b.order);

  return (
    <div style={{
      minHeight: "100vh",
      background: palette.bg,
      color: palette.fg,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif',
    }}>
      {/* Header */}
      <header style={{
        padding: "1rem 1.5rem",
        borderBottom: `1px solid ${palette.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>
            {data?.today.greeting || "Dashboard"}
          </h1>
          <p style={{ fontSize: "0.875rem", color: palette.muted, margin: "0.25rem 0 0" }}>
            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
          </p>
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={{
            background: "none",
            border: "none",
            color: palette.muted,
            cursor: "pointer",
            padding: "0.5rem",
          }}
        >
          <IconSettings size={20} />
        </button>
      </header>

      {/* Quick Actions */}
      <div style={{
        padding: "1rem 1.5rem",
        display: "flex",
        gap: "0.75rem",
      }}>
        <QuickActionButton
          icon={<IconMessageCircle size={18} />}
          label="Talk to Sakhi"
          onClick={() => router.push(`/experience/converse?user=${personId}` as Route)}
        />
        <QuickActionButton
          icon={<IconMic size={18} />}
          label="Voice"
          onClick={() => router.push(`/experience/voice?user=${personId}` as Route)}
        />
        <QuickActionButton
          icon={<IconCalendar size={18} />}
          label="Calendar"
          onClick={() => router.push(`/experience/calendar?user=${personId}` as Route)}
        />
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <SettingsPanel
          widgets={widgetConfig}
          onToggle={toggleWidget}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* Widget Grid */}
      <div style={{ padding: "0 1.5rem 2rem" }}>
        {sortedWidgets.map((widget) => {
          if (!widget.visible) return null;

          switch (widget.id) {
            case "today":
              return <TodayWidget key={widget.id} data={data?.today} />;
            case "energy":
              return <EnergyWidget key={widget.id} data={data?.energy ?? null} personId={personId} />;
            case "relationships":
              return <RelationshipsWidget key={widget.id} data={data?.relationships} />;
            case "calendar":
              return <CalendarWidget key={widget.id} events={data?.upcoming?.events || []} personId={personId} />;
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
}

// =============================================================================
// QUICK ACTION BUTTON
// =============================================================================

function QuickActionButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.75rem",
        background: palette.cardBg,
        border: `1px solid ${palette.border}`,
        borderRadius: "12px",
        color: palette.fg,
        cursor: "pointer",
        transition: "all 150ms ease",
      }}
    >
      <span style={{ color: palette.accent }}>{icon}</span>
      <span style={{ fontSize: "0.75rem", color: palette.muted }}>{label}</span>
    </button>
  );
}

// =============================================================================
// SETTINGS PANEL
// =============================================================================

function SettingsPanel({
  widgets,
  onToggle,
  onClose,
}: {
  widgets: WidgetConfig[];
  onToggle: (id: string) => void;
  onClose: () => void;
}) {
  const widgetLabels: Record<string, string> = {
    today: "Today's Schedule",
    energy: "Energy & State",
    relationships: "Relationships",
    calendar: "Upcoming Events",
  };

  return (
    <div style={{
      margin: "0 1.5rem 1rem",
      padding: "1rem",
      background: palette.cardBg,
      border: `1px solid ${palette.border}`,
      borderRadius: "12px",
    }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "1rem",
      }}>
        <h3 style={{ margin: 0, fontSize: "0.875rem", fontWeight: 500 }}>
          Customize Dashboard
        </h3>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: palette.muted,
            cursor: "pointer",
            fontSize: "1rem",
          }}
        >
          ×
        </button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {widgets.map((widget) => (
          <label
            key={widget.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              padding: "0.5rem",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={widget.visible}
              onChange={() => onToggle(widget.id)}
              style={{ accentColor: palette.accent }}
            />
            <span style={{ fontSize: "0.875rem", color: palette.fg }}>
              {widgetLabels[widget.id] || widget.id}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// TODAY WIDGET
// =============================================================================

function TodayWidget({ data }: { data?: DashboardData["today"] }) {
  if (!data) return null;

  return (
    <WidgetCard title="Today" icon={<IconSun size={18} />}>
      {data.events.length === 0 ? (
        <p style={{ color: palette.muted, fontSize: "0.875rem", margin: 0 }}>
          No events scheduled for today
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {data.events.slice(0, 4).map((event) => (
            <EventItem key={event.id} event={event} />
          ))}
          {data.event_count > 4 && (
            <p style={{ color: palette.muted, fontSize: "0.75rem", margin: 0 }}>
              +{data.event_count - 4} more events
            </p>
          )}
        </div>
      )}
    </WidgetCard>
  );
}

function EventItem({ event }: { event: CalendarEvent }) {
  const startTime = new Date(event.start_time).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });

  const typeColors: Record<string, string> = {
    meeting: palette.accent,
    social: palette.success,
    work: palette.warning,
    personal: palette.muted,
  };

  return (
    <div style={{
      display: "flex",
      alignItems: "flex-start",
      gap: "0.75rem",
      padding: "0.5rem",
      background: palette.bg,
      borderRadius: "8px",
    }}>
      <div style={{
        width: "3px",
        height: "100%",
        minHeight: "32px",
        background: typeColors[event.event_type] || palette.muted,
        borderRadius: "2px",
      }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{event.title}</div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "0.25rem",
          fontSize: "0.75rem",
          color: palette.muted,
          marginTop: "0.25rem",
        }}>
          <IconClock size={12} />
          {startTime}
          {event.energy_required && (
            <span style={{
              marginLeft: "0.5rem",
              padding: "0.125rem 0.375rem",
              background: `${palette.accent}22`,
              color: palette.accent,
              borderRadius: "4px",
              fontSize: "0.625rem",
              textTransform: "uppercase",
            }}>
              {event.energy_required}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ENERGY WIDGET
// =============================================================================

function EnergyWidget({ data, personId }: { data: FrictionState | null; personId: string }) {
  const router = useRouter();

  const frictionColors: Record<string, string> = {
    chaos: palette.chaos,
    intensity: palette.intensity,
    stagnation: palette.stagnation,
    balanced: palette.balanced,
  };

  const frictionState = data?.friction_state?.toLowerCase() || "";
  const frictionColor = frictionColors[frictionState] || palette.muted;

  return (
    <WidgetCard
      title="Energy & State"
      icon={<IconZap size={18} />}
      onTap={() => router.push(`/experience/me?user=${personId}` as Route)}
    >
      {!data ? (
        <p style={{ color: palette.muted, fontSize: "0.875rem", margin: 0 }}>
          Share how you&apos;re feeling to see your state
        </p>
      ) : (
        <div>
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: "0.75rem", flexWrap: "wrap" }}>
            {/* Friction State */}
            <div style={{
              background: `${frictionColor}22`,
              border: `1px solid ${frictionColor}`,
              borderRadius: "8px",
              padding: "0.5rem 0.75rem",
            }}>
              <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase" }}>
                State
              </div>
              <div style={{ color: frictionColor, fontWeight: 600, textTransform: "capitalize" }}>
                {data.friction_name || frictionState || "Unknown"}
              </div>
            </div>

            {/* Drift */}
            {data.drift_percentage !== undefined && (
              <div style={{
                background: palette.bg,
                border: `1px solid ${palette.border}`,
                borderRadius: "8px",
                padding: "0.5rem 0.75rem",
              }}>
                <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase" }}>
                  Drift
                </div>
                <div style={{
                  color: data.drift_percentage > 50 ? palette.warning : palette.fg,
                  fontWeight: 600,
                }}>
                  {Math.round(data.drift_percentage)}%
                </div>
              </div>
            )}

            {/* OS Type */}
            {data.operating_system && (
              <div style={{
                background: `${palette.accent}22`,
                border: `1px solid ${palette.accent}`,
                borderRadius: "8px",
                padding: "0.5rem 0.75rem",
              }}>
                <div style={{ fontSize: "0.625rem", color: palette.muted, textTransform: "uppercase" }}>
                  Type
                </div>
                <div style={{ color: palette.accent, fontWeight: 600, fontSize: "0.875rem" }}>
                  {data.operating_system}
                </div>
              </div>
            )}
          </div>

          {data.description && (
            <p style={{
              fontSize: "0.875rem",
              color: palette.muted,
              margin: 0,
              lineHeight: 1.5,
            }}>
              {data.description}
            </p>
          )}
        </div>
      )}
    </WidgetCard>
  );
}

// =============================================================================
// RELATIONSHIPS WIDGET
// =============================================================================

function RelationshipsWidget({ data }: { data?: DashboardData["relationships"] }) {
  return (
    <WidgetCard title="Connections" icon={<IconUsers size={18} />}>
      {!data || data.needing_attention.length === 0 ? (
        <p style={{ color: palette.muted, fontSize: "0.875rem", margin: 0 }}>
          All your close connections are up to date
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <p style={{ fontSize: "0.75rem", color: palette.muted, margin: 0 }}>
            Consider reaching out to:
          </p>
          {data.needing_attention.map((rel, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.5rem",
                background: palette.bg,
                borderRadius: "8px",
              }}
            >
              <div style={{
                width: "36px",
                height: "36px",
                borderRadius: "50%",
                background: `${palette.accent}33`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: palette.accent,
                fontWeight: 600,
                fontSize: "0.875rem",
              }}>
                {rel.name.charAt(0).toUpperCase()}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{rel.name}</div>
                <div style={{ fontSize: "0.75rem", color: palette.muted }}>
                  {rel.days_since_contact !== undefined
                    ? `${rel.days_since_contact} days since last contact`
                    : rel.relationship_type}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

// =============================================================================
// CALENDAR WIDGET
// =============================================================================

function CalendarWidget({ events, personId }: { events: CalendarEvent[]; personId: string }) {
  const router = useRouter();

  return (
    <WidgetCard
      title="Upcoming"
      icon={<IconCalendar size={18} />}
      onTap={() => router.push(`/experience/calendar?user=${personId}` as Route)}
    >
      {events.length === 0 ? (
        <p style={{ color: palette.muted, fontSize: "0.875rem", margin: 0 }}>
          No upcoming events
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {events.slice(0, 3).map((event) => {
            const date = new Date(event.start_time);
            const isToday = date.toDateString() === new Date().toDateString();
            const isTomorrow = date.toDateString() === new Date(Date.now() + 86400000).toDateString();

            let dayLabel = date.toLocaleDateString("en-US", { weekday: "short" });
            if (isToday) dayLabel = "Today";
            if (isTomorrow) dayLabel = "Tomorrow";

            const timeLabel = date.toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
            });

            return (
              <div
                key={event.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  fontSize: "0.875rem",
                }}
              >
                <div style={{
                  minWidth: "60px",
                  fontSize: "0.75rem",
                  color: isToday ? palette.accent : palette.muted,
                }}>
                  {dayLabel}
                </div>
                <div style={{ flex: 1, fontWeight: 500 }}>{event.title}</div>
                <div style={{ fontSize: "0.75rem", color: palette.muted }}>{timeLabel}</div>
              </div>
            );
          })}
        </div>
      )}
    </WidgetCard>
  );
}

// =============================================================================
// WIDGET CARD
// =============================================================================

function WidgetCard({
  title,
  icon,
  children,
  onTap,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  onTap?: () => void;
}) {
  return (
    <div
      style={{
        background: palette.cardBg,
        border: `1px solid ${palette.border}`,
        borderRadius: "12px",
        padding: "1rem",
        marginBottom: "1rem",
        cursor: onTap ? "pointer" : "default",
        transition: "border-color 150ms ease",
      }}
      onClick={onTap}
    >
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        marginBottom: "0.75rem",
      }}>
        {icon && <span style={{ color: palette.accent }}>{icon}</span>}
        <h3 style={{ margin: 0, fontSize: "0.875rem", fontWeight: 500 }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

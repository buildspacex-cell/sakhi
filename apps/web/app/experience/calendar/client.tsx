"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// ─────────────────────────────────────────────────────────────
// Inline SVG Icons
// ─────────────────────────────────────────────────────────────
const IconArrowLeft = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>
);

const IconCalendar = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const IconClock = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconUsers = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

const IconZap = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const IconChevronLeft = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6" />
  </svg>
);

const IconChevronRight = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6" />
  </svg>
);

const IconMapPin = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);

const IconPlus = ({ size = 18 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19" />
    <line x1="5" y1="12" x2="19" y2="12" />
  </svg>
);

// ─────────────────────────────────────────────────────────────
// Palette (matching Me page)
// ─────────────────────────────────────────────────────────────
const palette = {
  bg: "#0e0f12",
  fg: "#f4f4f5",
  muted: "#a1a1aa",
  accent: "#6366f1",
  cardBg: "#18191d",
  border: "#27272a",
  chaos: "#e8c547",
  intensity: "#ef6461",
  stagnation: "#4787e8",
  balanced: "#22c55e",
  // Event types
  meeting: "#6366f1",
  social: "#22c55e",
  personal: "#e8c547",
  work: "#ef6461",
  blocked: "#a1a1aa",
  focus_time: "#4ecdc4",
  recovery: "#9333ea",
};

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────
interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  location?: string;
  event_type: string;
  energy_required?: string;
  relationship_note?: string;
  energy_note?: string;
  created_by?: string;
}

interface WeekSummary {
  event_count: number;
  energy_prediction?: string;
  busiest_day?: string;
  relationship_events?: number;
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────
export default function CalendarPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const userId = searchParams.get("user") || "test-user";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [todayEvents, setTodayEvents] = useState<CalendarEvent[]>([]);
  const [weekEvents, setWeekEvents] = useState<CalendarEvent[]>([]);
  const [weekSummary, setWeekSummary] = useState<WeekSummary | null>(null);

  // UI states
  const [view, setView] = useState<"today" | "week">("today");
  const [selectedDate, setSelectedDate] = useState(new Date());

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [todayRes, weekRes, summaryRes] = await Promise.all([
          fetch(`/api/calendar/today?user=${userId}`).catch(() => null),
          fetch(`/api/calendar/week?user=${userId}`).catch(() => null),
          fetch(`/api/calendar/summary?user=${userId}`).catch(() => null),
        ]);

        if (todayRes?.ok) {
          const data = await todayRes.json();
          setTodayEvents(Array.isArray(data) ? data : data.events || []);
        }
        if (weekRes?.ok) {
          const data = await weekRes.json();
          setWeekEvents(Array.isArray(data) ? data : data.events || []);
        }
        if (summaryRes?.ok) {
          const data = await summaryRes.json();
          setWeekSummary(data);
        }
      } catch (err) {
        setError("Failed to load calendar");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [userId]);

  const handleBack = () => router.push(`/experience/converse?user=${userId}`);
  const handleSchedule = () => router.push(`/experience/converse?user=${userId}&prompt=schedule`);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: palette.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: palette.muted }}>Loading calendar...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: "100vh", background: palette.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: palette.intensity }}>{error}</div>
      </div>
    );
  }

  const today = new Date();
  const dayName = today.toLocaleDateString("en-US", { weekday: "long" });
  const dateStr = today.toLocaleDateString("en-US", { month: "long", day: "numeric" });

  return (
    <div style={{ minHeight: "100vh", background: palette.bg, color: palette.fg, padding: "1rem" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.5rem" }}>
        <button
          onClick={handleBack}
          style={{
            background: "transparent",
            border: "none",
            color: palette.muted,
            cursor: "pointer",
            padding: "0.5rem",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
          }}
        >
          <IconArrowLeft size={20} />
        </button>
        <div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 600, margin: 0 }}>
            <IconCalendar size={22} /> Calendar
          </h1>
          <p style={{ color: palette.muted, fontSize: "0.875rem", margin: 0 }}>
            {dayName}, {dateStr}
          </p>
        </div>
      </div>

      {/* View Toggle */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button
          onClick={() => setView("today")}
          style={{
            flex: 1,
            padding: "0.75rem",
            background: view === "today" ? palette.accent : palette.cardBg,
            border: `1px solid ${view === "today" ? palette.accent : palette.border}`,
            borderRadius: 8,
            color: palette.fg,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          Today
        </button>
        <button
          onClick={() => setView("week")}
          style={{
            flex: 1,
            padding: "0.75rem",
            background: view === "week" ? palette.accent : palette.cardBg,
            border: `1px solid ${view === "week" ? palette.accent : palette.border}`,
            borderRadius: 8,
            color: palette.fg,
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          This Week
        </button>
      </div>

      {/* Week Summary Card */}
      {weekSummary && (
        <div style={{
          background: palette.cardBg,
          borderRadius: 12,
          padding: "1rem",
          marginBottom: "1rem",
          border: `1px solid ${palette.border}`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ fontSize: "1.25rem", fontWeight: 600 }}>{weekSummary.event_count}</span>
              <span style={{ color: palette.muted, marginLeft: "0.5rem" }}>events this week</span>
            </div>
            {weekSummary.energy_prediction && (
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "0.25rem",
                color: palette.balanced,
                fontSize: "0.875rem",
              }}>
                <IconZap size={14} />
                {weekSummary.energy_prediction}
              </div>
            )}
          </div>
          {weekSummary.busiest_day && (
            <p style={{ color: palette.muted, fontSize: "0.75rem", marginTop: "0.5rem", marginBottom: 0 }}>
              Busiest: {weekSummary.busiest_day}
            </p>
          )}
        </div>
      )}

      {/* Events List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {view === "today" ? (
          todayEvents.length === 0 ? (
            <EmptyState message="No events today" onSchedule={handleSchedule} />
          ) : (
            todayEvents.map((event) => (
              <EventCard key={event.id} event={event} />
            ))
          )
        ) : (
          weekEvents.length === 0 ? (
            <EmptyState message="No events this week" onSchedule={handleSchedule} />
          ) : (
            <WeekView events={weekEvents} />
          )
        )}
      </div>

      {/* Floating Action Button */}
      <button
        onClick={handleSchedule}
        style={{
          position: "fixed",
          bottom: "2rem",
          right: "1rem",
          width: 56,
          height: 56,
          borderRadius: 28,
          background: palette.accent,
          border: "none",
          color: palette.fg,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 4px 12px rgba(99, 102, 241, 0.4)",
        }}
        title="Schedule with Sakhi"
      >
        <IconPlus size={24} />
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Event Card Component
// ─────────────────────────────────────────────────────────────
function EventCard({ event }: { event: CalendarEvent }) {
  const startTime = new Date(event.start_time);
  const endTime = new Date(event.end_time);

  const timeStr = `${startTime.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })} - ${endTime.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`;

  const eventColor = palette[event.event_type as keyof typeof palette] || palette.personal;

  return (
    <div style={{
      background: palette.cardBg,
      borderRadius: 12,
      padding: "1rem",
      border: `1px solid ${palette.border}`,
      borderLeft: `4px solid ${eventColor}`,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 500, margin: 0, marginBottom: "0.25rem" }}>
            {event.title}
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: palette.muted, fontSize: "0.875rem" }}>
            <IconClock size={14} />
            {timeStr}
          </div>
        </div>
        <span style={{
          background: `${eventColor}22`,
          color: eventColor,
          padding: "0.25rem 0.5rem",
          borderRadius: 8,
          fontSize: "0.75rem",
          textTransform: "capitalize",
        }}>
          {event.event_type.replace("_", " ")}
        </span>
      </div>

      {event.location && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: palette.muted, fontSize: "0.75rem", marginTop: "0.5rem" }}>
          <IconMapPin size={12} />
          {event.location}
        </div>
      )}

      {event.relationship_note && (
        <div style={{
          marginTop: "0.75rem",
          paddingTop: "0.5rem",
          borderTop: `1px solid ${palette.border}`,
          fontSize: "0.75rem",
          color: palette.accent,
          fontStyle: "italic",
        }}>
          <IconUsers size={12} /> {event.relationship_note}
        </div>
      )}

      {event.energy_note && (
        <div style={{
          marginTop: "0.5rem",
          fontSize: "0.75rem",
          color: palette.chaos,
        }}>
          <IconZap size={12} /> {event.energy_note}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Week View Component
// ─────────────────────────────────────────────────────────────
function WeekView({ events }: { events: CalendarEvent[] }) {
  // Group events by day
  const eventsByDay: Record<string, CalendarEvent[]> = {};

  events.forEach((event) => {
    const date = new Date(event.start_time).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
    if (!eventsByDay[date]) eventsByDay[date] = [];
    eventsByDay[date].push(event);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {Object.entries(eventsByDay).map(([date, dayEvents]) => (
        <div key={date}>
          <h4 style={{ fontSize: "0.875rem", color: palette.muted, marginBottom: "0.5rem", fontWeight: 500 }}>
            {date}
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {dayEvents.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Empty State Component
// ─────────────────────────────────────────────────────────────
function EmptyState({ message, onSchedule }: { message: string; onSchedule: () => void }) {
  return (
    <div style={{
      background: palette.cardBg,
      borderRadius: 12,
      padding: "2rem",
      textAlign: "center",
      border: `1px solid ${palette.border}`,
    }}>
      <IconCalendar size={48} />
      <p style={{ color: palette.muted, marginTop: "1rem", marginBottom: "1rem" }}>
        {message}
      </p>
      <button
        onClick={onSchedule}
        style={{
          background: palette.accent,
          border: "none",
          color: palette.fg,
          padding: "0.75rem 1.5rem",
          borderRadius: 8,
          cursor: "pointer",
          fontWeight: 500,
        }}
      >
        Schedule Something
      </button>
    </div>
  );
}

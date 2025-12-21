"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import RhythmDashboard from "@/components/RhythmDashboard";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type Summary = {
  clarity_index?: number;
  energy_index?: number;
  dominant_tone?: string;
};

type SeriesPoint = {
  day: string;
  clarity: number;
  energy: number;
};

type BreathPoint = {
  day: string;
  rate: number;
  calm: number;
};

type RhythmState = {
  body_energy?: number;
  mind_focus?: number;
  emotion_tone?: string;
  fatigue_level?: number;
  stress_level?: number;
  chronotype?: string;
  next_peak?: string | null;
  next_lull?: string | null;
  rhythm_alignment?: Record<string, any>;
};

type RhythmCurveResponse = {
  days?: Array<{ day_scope: string; slots: Array<{ time: string; energy: number }>; confidence?: number }>;
  alignment?: Record<string, any>;
};

const PERSON_ID =
  process.env.NEXT_PUBLIC_DEMO_PERSON_ID ||
  process.env.NEXT_PUBLIC_PERSON_ID ||
  "demo-user";

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary>({});
  const [data, setData] = useState<SeriesPoint[]>([]);
  const [breathData, setBreathData] = useState<BreathPoint[]>([]);
  const [rhythmState, setRhythmState] = useState<RhythmState | null>(null);
  const [rhythmCurve, setRhythmCurve] = useState<RhythmCurveResponse | null>(
    null,
  );

  useEffect(() => {
    fetch(`/api/analytics/summary/${PERSON_ID}`)
      .then((res) => res.json())
      .then(setSummary)
      .catch(() => setSummary({}));

    fetch(`/api/analytics/timeseries/${PERSON_ID}`)
      .then((res) => res.json())
      .then(setData)
      .catch(() => setData([]));

    fetch(`/api/analytics/breath/${PERSON_ID}`)
      .then((res) => res.json())
      .then(setBreathData)
      .catch(() => setBreathData([]));

    fetch(`/api/rhythm/state/${PERSON_ID}`)
      .then((res) => res.json())
      .then(setRhythmState)
      .catch(() => setRhythmState(null));

    fetch(`/api/rhythm/curve/${PERSON_ID}`)
      .then((res) => res.json())
      .then(setRhythmCurve)
      .catch(() => setRhythmCurve(null));
  }, []);

  const latestBreath = breathData[breathData.length - 1];
  const coherenceIndicator =
    latestBreath && typeof latestBreath.calm === "number"
      ? Math.round(latestBreath.calm * 100)
      : null;

  const rhythmSeries =
    rhythmCurve?.days?.map((day) => {
      const energyValues = day.slots?.map((slot) => slot.energy) ?? [];
      const avgEnergy =
        energyValues.length > 0
          ? energyValues.reduce((a, b) => a + b, 0) / energyValues.length
          : 0;
      return {
        day: day.day_scope,
        energy: Number(avgEnergy.toFixed(2)),
        mood: Number(rhythmState?.mind_focus ?? 0),
      };
    }) ?? [];

  const plannerAlignment =
    (rhythmCurve?.alignment?.today as Array<any>) ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-rose-50 p-6 space-y-6">
      <h1 className="text-xl font-semibold text-rose-700">Your Weekly Flow</h1>
      <Card className="shadow-md">
        <CardContent className="p-4">
          <p className="text-sm text-gray-700 mb-2 space-x-4">
            <span>
              Clarity Index: <b>{summary.clarity_index ?? "--"}</b>
            </span>
            <span>
              Energy Index: <b>{summary.energy_index ?? "--"}</b>
            </span>
            <span>
              Mood: <b>{summary.dominant_tone ?? "--"}</b>
            </span>
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data}>
              <XAxis dataKey="day" hide />
              <YAxis hide domain={[0, 1]} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="clarity"
                stroke="#f43f5e"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="energy"
                stroke="#fb923c"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card className="shadow-md">
        <CardContent className="p-4">
          <div className="flex justify-between items-center mb-2">
            <p className="text-sm text-gray-700">
              Breath Rhythm — 30 Day Trend
            </p>
            <p className="text-sm text-rose-600">
              Tempo Coherence:{" "}
              <b>{coherenceIndicator !== null ? `${coherenceIndicator}%` : "--"}</b>
            </p>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={breathData}>
              <XAxis dataKey="day" hide />
              <YAxis hide />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="rate"
                stroke="#fb7185"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="calm"
                stroke="#22d3ee"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
      <Card className="shadow-md">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Rhythm Snapshot</p>
              <p className="text-xs text-gray-500">
                Chronotype:{" "}
                <b>{rhythmState?.chronotype ?? "intermediate"}</b>
              </p>
            </div>
            <div className="text-sm text-gray-700 space-x-4">
              <span>
                Energy:{" "}
                <b>
                  {rhythmState?.body_energy !== undefined
                    ? Math.round((rhythmState.body_energy ?? 0) * 100)
                    : "--"}
                  %
                </b>
              </span>
              <span>
                Stress:{" "}
                <b>
                  {rhythmState?.stress_level !== undefined
                    ? Math.round((rhythmState.stress_level ?? 0) * 100)
                    : "--"}
                  %
                </b>
              </span>
              <span>
                Fatigue:{" "}
                <b>
                  {rhythmState?.fatigue_level !== undefined
                    ? Math.round((rhythmState.fatigue_level ?? 0) * 100)
                    : "--"}
                  %
                </b>
              </span>
            </div>
          </div>
          <RhythmDashboard data={rhythmSeries} />
          <div>
            <p className="text-sm text-gray-600 mb-2">
              Planner Alignment (today)
            </p>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {plannerAlignment.length ? (
                plannerAlignment.map((rec, idx) => (
                  <div
                    key={`${rec.window}-${idx}`}
                    className="rounded-xl bg-white/80 px-3 py-2 text-sm shadow-sm"
                  >
                    <p className="font-semibold text-rose-600">{rec.window}</p>
                    <p className="text-gray-600 capitalize">
                      {rec.energy} energy
                    </p>
                    <p className="text-xs text-gray-500">
                      Fits: {(rec.fit || []).join(", ")}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">
                  Rhythm alignment will appear after a few sessions.
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

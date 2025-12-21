"use client";

import * as React from "react";

import { api, fetchPersonModel, fetchPersonSummary } from "@/lib/api";
import { InnerViewPanel, PersonalModel as LayeredPersonalModel } from "@/components/InnerViewPanel";

interface PersonSummary {
  person_id: string;
  goals: any[];
  values_prefs: any[];
  themes: any[];
  avg_mood_7d: number | null;
  aspect_snapshot: any[];
}

interface PersonModelTheme {
  theme: string;
  domain?: string | null;
  description: string;
  salience: number;
  significance: number;
  emotion: number;
  impact: number;
  examples: string[];
}

type PersonalModelSnapshot = Record<string, unknown> & {
  themes?: PersonModelTheme[];
};

const friendlyLabels: Record<string, string> = {
  intent: "Goal Orientation",
  time_scope: "Time Frame",
  moods: "Mood Signals",
  themes: "Themes",
  goal: "Goal Highlight",
};

export default function PersonModelPanel({
  personId,
  summary: initial,
  model: initialModel,
}: {
  personId: string;
  summary?: PersonSummary | null;
  model?: Record<string, unknown> | null;
}) {
  const [summary, setSummary] = React.useState<PersonSummary | null>(initial ?? null);
  const [model, setModel] = React.useState<PersonalModelSnapshot | null>(
    (initialModel as PersonalModelSnapshot | null) ?? null,
  );
  const [layerModel, setLayerModel] = React.useState<LayeredPersonalModel | null>(
    (initialModel?.data as LayeredPersonalModel) ?? null,
  );
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [pendingGoal, setPendingGoal] = React.useState<string | null>(null);
  const [pendingPref, setPendingPref] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (!personId) return;
    setLoading(true);
    setError(null);
    try {
      const [summaryData, modelData] = await Promise.all([
        fetchPersonSummary(personId),
        fetchPersonModel(personId),
      ]);
      if (summaryData) {
        setSummary(summaryData);
      }
      setModel((modelData as PersonalModelSnapshot) ?? null);
      if (modelData && typeof modelData === "object") {
        setLayerModel(((modelData as any).data ?? null) as LayeredPersonalModel | null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh person model");
    } finally {
      setLoading(false);
    }
  }, [personId]);

  React.useEffect(() => {
    if (personId && (!summary || !model)) {
      refresh();
    }
  }, [personId, refresh, summary, model]);

  React.useEffect(() => {
    if (initial) {
      setSummary(initial);
    }
  }, [initial]);

  React.useEffect(() => {
    if (typeof initialModel === "undefined") {
      return;
    }
    if (initialModel) {
      setModel((initialModel as PersonalModelSnapshot) ?? null);
      setLayerModel(((initialModel as any).data ?? null) as LayeredPersonalModel | null);
    } else {
      setModel(null);
      setLayerModel(null);
    }
  }, [initialModel]);

  const handleGoalConfirm = async (goal: any) => {
    if (!personId || !goal?.title) return;
    setPendingGoal(goal.title);
    setError(null);
    try {
      await api.person.goalUpsert({
        person_id: personId,
        title: goal.title,
        status: "active",
        horizon: goal.horizon ?? goal.timescale ?? "month",
        progress: typeof goal.progress === "number" ? goal.progress : 0,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm goal");
    } finally {
      setPendingGoal(null);
    }
  };

  const handlePrefConfirm = async (pref: any) => {
    if (!personId || !pref?.key) return;
    setPendingPref(pref.key);
    setError(null);
    try {
      const value = typeof pref.value === "object" && pref.value ? pref.value : { value: pref.value };
      await api.person.preferenceUpsert({
        person_id: personId,
        scope: pref.scope ?? "values",
        key: pref.key,
        value,
        confidence: 0.9,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm preference");
    } finally {
      setPendingPref(null);
    }
  };

  if (!summary && !model) {
    return <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-500">Loading...</div>;
  }

  const themes = Array.isArray(model?.themes) ? (model?.themes as PersonModelTheme[]) : [];
  const narrativePieces: string[] = [];
  if (layerModel?.goals?.summary) narrativePieces.push(layerModel.goals.summary);
  if (layerModel?.emotion?.summary) narrativePieces.push(layerModel.emotion.summary);
  if (layerModel?.mind?.summary) narrativePieces.push(layerModel.mind.summary);
  if (layerModel?.rhythm?.summary) narrativePieces.push(layerModel.rhythm.summary);
  const narrativeText = narrativePieces.join(" ");
  const miscEntries: Array<[string, unknown]> = [];
  const goals = Array.isArray(summary?.goals) ? (summary?.goals as any[]) : [];
  const preferences = Array.isArray(summary?.values_prefs) ? (summary?.values_prefs as any[]) : [];
  const formatPercent = (value: number | null | undefined) =>
    typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(0)}%` : "—";
  const formatDescription = (value: string | null | undefined) =>
    value && value.trim().length > 0 ? value : "Theme derived from your journaling patterns.";
  const renderGoal = (goal: any) => {
    const status = goal.status ?? goal.state ?? "unknown";
    const isProposed = String(status).toLowerCase() === "proposed";
    return (
      <div key={goal.id ?? goal.title} className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-3 py-2">
        <div>
          <div className="text-sm font-medium text-zinc-800">{goal.title ?? goal.name ?? "Untitled"}</div>
          <div className="text-xs text-zinc-500">{status}</div>
          {goal.horizon && <div className="text-xs text-zinc-400">Horizon: {goal.horizon}</div>}
        </div>
        {isProposed && (
          <button
            type="button"
            onClick={() => handleGoalConfirm(goal)}
            disabled={pendingGoal === goal.title || loading}
            className="text-xs font-medium text-orange-600 hover:text-orange-700 disabled:text-zinc-400"
          >
            {pendingGoal === goal.title ? "Saving…" : "Confirm"}
          </button>
        )}
      </div>
    );
  };

  const renderPref = (pref: any) => {
    const confidence = typeof pref.confidence === "number" ? pref.confidence : null;
    const isLowConfidence = confidence !== null && confidence < 0.8;
    const valuePreview =
      typeof pref.value === "string"
        ? pref.value
        : typeof pref.value === "object" && pref.value
        ? JSON.stringify(pref.value)
        : "—";
    return (
      <div key={pref.key ?? pref.id} className="flex items-start justify-between gap-2 rounded border border-zinc-200 bg-white px-3 py-2">
        <div>
          <div className="text-sm font-medium text-zinc-800">{pref.key ?? "Preference"}</div>
          <div className="text-xs text-zinc-500">{valuePreview}</div>
          {confidence !== null && (
            <div className="text-xs text-zinc-400">Confidence: {(confidence * 100).toFixed(0)}%</div>
          )}
        </div>
        {isLowConfidence && (
          <button
            type="button"
            onClick={() => handlePrefConfirm(pref)}
            disabled={pendingPref === pref.key || loading}
            className="text-xs font-medium text-orange-600 hover:text-orange-700 disabled:text-zinc-400"
          >
            {pendingPref === pref.key ? "Saving…" : "Confirm"}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-3 rounded-xl border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
      <div className="flex items-center justify-between">
        <div className="font-semibold">Personal Model</div>
        <button
          type="button"
          onClick={refresh}
          className="text-xs text-orange-600 hover:text-orange-700"
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>
      {error && <div className="rounded bg-red-50 px-2 py-1 text-xs text-red-600">{error}</div>}
      <InnerViewPanel model={layerModel} />
      <h3 className="mt-6 font-semibold">Personal Model</h3>
      {narrativeText && (
        <div className="rounded-xl bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm">
          {narrativeText}
        </div>
      )}
      <div className="space-y-3">
        {themes.length > 0 &&
          themes.map((t) => (
            <div key={t.theme} className="rounded-xl bg-white/60 p-3 shadow">
              <div className="font-semibold text-zinc-800">{t.theme}</div>
              <div className="mb-2 text-xs text-muted-foreground">{formatDescription(t.description)}</div>
              <div className="text-xs text-zinc-600">Domain: {t.domain ?? "—"}</div>
              <div className="text-xs text-zinc-600">Emotional tone: {formatPercent(t.emotion)}</div>
              <div className="text-xs text-zinc-600">Significance: {formatPercent(t.significance)}</div>
              <div className="text-xs text-zinc-600">Salience (currently active): {formatPercent(t.salience)}</div>
              <div className="text-xs text-zinc-600">Impact: {formatPercent(t.impact)}</div>
              {Array.isArray(t.examples) && t.examples.length > 0 && (
                <div className="mt-2 space-y-1 text-xs text-zinc-500">
                  <div className="font-semibold text-zinc-700">Examples</div>
                  <ul className="list-disc space-y-1 pl-4">
                    {t.examples.slice(0, 3).map((ex) => (
                      <li key={ex}>{ex}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

        {miscEntries.length > 0 && (
          <div className="rounded-xl bg-white px-3 py-2 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Latest Signals</div>
            <div className="mt-2 space-y-1 text-xs text-zinc-600">
              {miscEntries.map(([key, value]) => {
                const label = friendlyLabels[key] ?? key;
                const rendered =
                  Array.isArray(value)
                    ? value.map((v) => String(v)).join(", ")
                    : typeof value === "object" && value !== null
                    ? JSON.stringify(value)
                    : String(value ?? "—");
                return (
                  <div key={key} className="flex justify-between gap-2">
                    <span className="font-medium text-zinc-700">{label}</span>
                    <span className="text-right text-zinc-500">{rendered}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {themes.length === 0 && miscEntries.length === 0 && (
          <div className="rounded-lg bg-white/60 p-3 text-xs text-zinc-500">
            No personal themes captured yet.
          </div>
        )}
      </div>

      {goals.length > 0 && (
        <section className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Goals</h4>
          <div className="space-y-2">
            {goals.map(renderGoal)}
          </div>
        </section>
      )}

      {preferences.length > 0 && (
        <section className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Preferences & Guardrails</h4>
          <div className="space-y-2">
            {preferences.map(renderPref)}
          </div>
        </section>
      )}
    </div>
  );
}

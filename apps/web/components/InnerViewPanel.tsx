import * as React from "react";

export type LayerState = {
  summary?: string | null;
  confidence?: number | null;
  metrics?: Record<string, unknown> | null;
};

export type PersonalModel = {
  body?: LayerState;
  mind?: LayerState;
  emotion?: LayerState;
  goals?: LayerState;
  soul?: LayerState;
  rhythm?: LayerState;
};

const layers: Array<[keyof PersonalModel, string]> = [
  ["body", "Body"],
  ["mind", "Mind"],
  ["emotion", "Emotion"],
  ["goals", "Goals"],
  ["soul", "Soul"],
  ["rhythm", "Rhythm"],
];

export function InnerViewPanel({ model }: { model: PersonalModel | null }) {
  return (
    <div className="rounded-2xl bg-white/40 p-4 shadow-sm backdrop-blur-sm">
      <h3 className="text-lg font-semibold mb-3">Sakhi’s Current Understanding</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {layers.map(([key, label]) => {
          const layer = model?.[key];
          return (
            <div key={key as string} className="rounded-xl bg-white/70 p-3 shadow-inner">
              <div className="text-sm font-medium text-slate-800">{label}</div>
              <p className="mt-1 text-sm text-slate-600">{layer?.summary || "—"}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}


export type GoalSummary = {
  id: string;
  title: string;
  horizon: string | null;
  progress: number | null;
};

export type PreferenceSummary = {
  scope: string;
  key: string;
  value: any;
  confidence: number;
};

export type ThemeSummary = {
  id: string;
  name: string;
  scope: string;
};

export type ActivitySummary = {
  layer: string;
  n: number;
};

export type AspectFeature = {
  aspect: string;
  key: string;
  value: any;
};

export type PersonSummary = {
  person_id: string;
  timeframes: {
    short_days: number;
    long_days: number;
  };
  overview: {
    goals: GoalSummary[];
    values_prefs: PreferenceSummary[];
    themes: ThemeSummary[];
    recent_activity: ActivitySummary[];
    short_tags: { t: string; n: number }[];
    long_tags: { t: string; n: number }[];
    avg_mood_short: number | null;
    salience_long: {
      avg: number | null;
      n: number;
    };
    anchor_weights: Record<string, number> | null;
  };
  aspect_snapshot: AspectFeature[];
};

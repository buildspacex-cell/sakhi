import dynamic from 'next/dynamic';
import type { CSSProperties } from 'react';

const PersonSnapshotForm = dynamic(() => import('@/components/PersonSnapshotForm'), { ssr: false });

type PlannerSummary = Record<string, any> | null;
type RhythmState = Record<string, any> | null;
type RhythmCurve = Record<string, any> | null;
type SoulSummary = Record<string, any> | null;
type MemorySynthesisCollection = { person_id: string; items: Array<Record<string, any>> } | null;
type MemoryBundle = {
  weekly: MemorySynthesisCollection;
  monthly: MemorySynthesisCollection;
};
type PersonalModelLayerCard = {
  key: string;
  label: string;
  summary: string;
  confidence: string;
};

type Snapshot = {
  person_id: string;
  journals: Array<{ id: string; text: string; full_text: string; layer?: string; mood?: string | null; tags?: string[]; created_at?: string }>;
  short_term_memory: Array<{ id: string; created_at?: string; text?: string; tags?: string[]; sentiment?: any; facets?: any }>;
  episodic_memory: Array<{ id: string; created_at?: string; text?: string; layer?: string; tags?: string[]; mood?: string | null }>;
  personal_model: {
    short_term: Record<string, any>;
    long_term: Record<string, any>;
    short_term_vector: Record<string, any>;
    updated_at?: string;
  };
  count: { journals: number; short_term: number; episodic: number };
  latest_prompt?: {
    user_text?: string;
    prompt?: string;
    system_context?: string;
    context?: Record<string, any>;
    tone?: Record<string, any>;
    error?: string;
  } | null;
};

const DEFAULT_PERSON_ID =
  process.env.NEXT_PUBLIC_DEMO_PERSON_ID ??
  process.env.DEMO_USER_ID ??
  '565bdb63-124b-4692-a039-846fddceff90';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const cardStyle: CSSProperties = {
  border: '1px solid rgba(249, 115, 22, 0.15)',
  borderRadius: '20px',
  padding: '1.25rem',
  background: 'rgba(255,255,255,0.92)',
  boxShadow: '0 20px 45px -24px rgba(249,115,22,0.45)',
};

function formatTimestamp(value?: string) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

async function fetchSnapshot(personId: string): Promise<Snapshot> {
  const url = new URL('/debug/person_snapshot', API_BASE);
  url.searchParams.set('person_id', personId);
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    const body = await response.text().catch(() => response.statusText);
    throw new Error(body || `Failed to load snapshot (${response.status})`);
  }
  return response.json();
}

async function fetchPlannerSummary(personId: string): Promise<PlannerSummary> {
  try {
    const response = await fetch(`${API_BASE}/planner/${personId}/summary`, { cache: 'no-store' });
    if (!response.ok) {
      console.warn("Planner summary unavailable", response.status);
      return null;
    }
    return response.json();
  } catch (error) {
    console.warn("Planner summary fetch failed", error);
    return null;
  }
}

async function fetchRhythmBundle(personId: string): Promise<{ state: RhythmState; curve: RhythmCurve }> {
  const [stateRes, curveRes] = await Promise.all([
    fetch(`${API_BASE}/rhythm/${personId}/state`, { cache: 'no-store' }),
    fetch(`${API_BASE}/rhythm/${personId}/curve`, { cache: 'no-store' }),
  ]);

  return {
    state: stateRes.ok ? await stateRes.json() : null,
    curve: curveRes.ok ? await curveRes.json() : null,
  };
}

async function fetchSoulSummary(personId: string): Promise<SoulSummary> {
  try {
    const response = await fetch(`${API_BASE}/soul/${personId}/summary`, { cache: 'no-store' });
    if (!response.ok) {
      console.warn("Soul summary unavailable", response.status);
      return null;
    }
    return response.json();
  } catch (error) {
    console.warn("Soul summary fetch failed", error);
    return null;
  }
}

async function fetchMemorySynthesis(personId: string): Promise<MemoryBundle> {
  const [weeklyRes, monthlyRes] = await Promise.all([
    fetch(`${API_BASE}/memory/${personId}/weekly`, { cache: 'no-store' }),
    fetch(`${API_BASE}/memory/${personId}/monthly`, { cache: 'no-store' }),
  ]);

  return {
    weekly: weeklyRes.ok ? await weeklyRes.json() : null,
    monthly: monthlyRes.ok ? await monthlyRes.json() : null,
  };
}

function buildPersonalModelLayers({
  snapshot,
  plannerSummary,
  rhythmState,
  soulSummary,
  memoryBundle,
}: {
  snapshot: Snapshot;
  plannerSummary: PlannerSummary;
  rhythmState: RhythmState;
  soulSummary: SoulSummary;
  memoryBundle: MemoryBundle;
}): PersonalModelLayerCard[] {
  const layersMap = new Map<string, PersonalModelLayerCard>();
  const longTerm = (snapshot.personal_model?.long_term ?? {}) as Record<string, any>;
  const rawLayers = (longTerm.layers ?? {}) as Record<string, any>;

  Object.entries(rawLayers).forEach(([layerKey, payload]) => {
    const summaryRaw =
      typeof payload?.summary === 'string' ? payload.summary : JSON.stringify(payload?.summary ?? '');
    const summary = summaryRaw && summaryRaw !== 'null' ? summaryRaw : '';
    const confidenceLabel =
      typeof payload?.confidence === 'number' && payload.confidence > 0
        ? `${Math.round(payload.confidence * 100)}% confidence`
        : 'confidence n/a';
    layersMap.set(layerKey, {
      key: layerKey,
      label: layerKey,
      summary: summary || 'No summary stored yet.',
      confidence: confidenceLabel,
    });
  });

  const upsertLayer = (key: string, summary?: string | null, confidence?: string | null) => {
    if (!summary || !summary.trim()) return;
    const previous = layersMap.get(key);
    layersMap.set(key, {
      key,
      label: previous?.label ?? key,
      summary,
      confidence: confidence ?? previous?.confidence ?? 'confidence n/a',
    });
  };

  if (plannerSummary && typeof plannerSummary === 'object') {
    const goals = Array.isArray(plannerSummary.goals) ? plannerSummary.goals : [];
    const goalNames = goals.map((goal: any) => goal?.title).filter(Boolean);
    const focusGoal =
      goalNames.length > 0 ? `${goalNames[0]}${goalNames.length > 1 ? ` (+${goalNames.length - 1} more)` : ''}` : null;
    const todayItems = Array.isArray(plannerSummary.today) ? plannerSummary.today : [];
    const weekItems = Array.isArray(plannerSummary.week) ? plannerSummary.week : [];
    const upcoming = [...todayItems, ...weekItems].find((item: any) => item && item.label);
    const summaryParts: string[] = [];
    if (focusGoal) summaryParts.push(`Focus: ${focusGoal}`);
    if (upcoming?.label) {
      const energy = upcoming.energy ? ` (${upcoming.energy} energy)` : '';
      summaryParts.push(`Next: ${upcoming.label}${energy}`);
    }
    const summaryText =
      summaryParts.join(' • ') || (goals.length ? `Tracking ${goals.length} goals` : 'Planner insights pending');
    const confidenceBits: string[] = [`${todayItems.length} today / ${weekItems.length} week tasks`];
    if (plannerSummary.source) confidenceBits.push(String(plannerSummary.source));
    upsertLayer('goals', summaryText, confidenceBits.filter(Boolean).join(' • '));
  }

  if (rhythmState && typeof rhythmState === 'object' && !Array.isArray(rhythmState)) {
    const toPercent = (value: any): string | null => {
      const num = Number(value);
      if (!Number.isFinite(num)) return null;
      return `${Math.round(num * 100)}%`;
    };
    const energy = toPercent((rhythmState as any).body_energy ?? (rhythmState as any).energy);
    const focus = toPercent((rhythmState as any).mind_focus);
    const tone = (rhythmState as any).emotion_tone;
    const summaryParts = [energy && `Energy ${energy}`, focus && `Focus ${focus}`, tone && `Tone ${tone}`].filter(Boolean);
    const confidenceParts: string[] = [];
    if ((rhythmState as any).chronotype) confidenceParts.push(`${(rhythmState as any).chronotype} chronotype`);
    if ((rhythmState as any).next_peak) confidenceParts.push(`Next peak ${formatTimestamp((rhythmState as any).next_peak)}`);
    if ((rhythmState as any).next_lull) confidenceParts.push(`Next lull ${formatTimestamp((rhythmState as any).next_lull)}`);
    upsertLayer('rhythm', summaryParts.join(' • '), confidenceParts.join(' • '));
  }

  if (soulSummary && typeof soulSummary === 'object') {
    const values = Array.isArray(soulSummary.values) ? soulSummary.values : [];
    const valueNames = values.map((value: any) => value?.value_name).filter(Boolean).slice(0, 2);
    const identity =
      Array.isArray(soulSummary.identity_signatures) && soulSummary.identity_signatures[0]
        ? soulSummary.identity_signatures[0].label
        : null;
    const purpose =
      Array.isArray(soulSummary.purpose_themes) && soulSummary.purpose_themes[0]
        ? soulSummary.purpose_themes[0].theme
        : null;
    const summaryParts: string[] = [];
    if (valueNames.length) summaryParts.push(`Values: ${valueNames.join(', ')}`);
    if (identity) summaryParts.push(`Identity: ${identity}`);
    if (purpose) summaryParts.push(`Purpose: ${purpose}`);
    const persona = soulSummary.persona_evolution ?? {};
    const personaMode = persona?.current_mode;
    const driftScoreValue =
      persona?.drift_score != null && persona.drift_score !== '' ? Number(persona.drift_score) : null;
    const driftLabel =
      typeof driftScoreValue === 'number' && Number.isFinite(driftScoreValue)
        ? `${Math.round(driftScoreValue * 100)}% drift`
        : null;
    const confidenceParts = [personaMode && `Mode ${personaMode}`, driftLabel].filter(Boolean);
    upsertLayer('soul', summaryParts.join(' • '), confidenceParts.join(' • '));
  }

  const weeklyItem = memoryBundle?.weekly?.items?.[0];
  if (weeklyItem) {
    const drift = typeof weeklyItem.drift_score === 'number' ? `${Math.round(weeklyItem.drift_score * 100)}% drift` : 'drift pending';
    const summary = weeklyItem.highlights || 'Weekly reflection pending.';
    upsertLayer('awareness', summary, `Weekly synthesis • ${drift}`);
  }

  const monthlyItem = memoryBundle?.monthly?.items?.[0];
  if (monthlyItem) {
    const drift = typeof monthlyItem.drift_score === 'number' ? `${Math.round(monthlyItem.drift_score * 100)}% drift` : 'drift pending';
    const chapter = monthlyItem.chapter_hint || 'Monthly reflection available.';
    upsertLayer('memory', chapter, `Monthly recap • ${drift}`);
  }

  return Array.from(layersMap.values());
}

function parseRecommendationList(raw: any): any[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

function toDisplay(value: any): string {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map((item) => toDisplay(item)).filter(Boolean).join(', ');
  if (typeof value === 'object') {
    if ('text' in value && typeof (value as any).text === 'string') return (value as any).text;
    return JSON.stringify(value);
  }
  return '';
}

export default async function PersonSnapshotPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>;
}) {
  const requestedId = typeof searchParams?.person_id === 'string' && searchParams.person_id ? searchParams.person_id : DEFAULT_PERSON_ID;
  let snapshot: Snapshot | null = null;
  let plannerSummary: PlannerSummary = null;
  let rhythmState: RhythmState = null;
  let rhythmCurve: RhythmCurve = null;
  let soulSummary: SoulSummary = null;
  let memorySynthesis: MemoryBundle = { weekly: null, monthly: null };
  let errorMessage: string | null = null;

  try {
    const [snap, planner, rhythm, soul, synthesisBundle] = await Promise.all([
      fetchSnapshot(requestedId),
      fetchPlannerSummary(requestedId),
      fetchRhythmBundle(requestedId),
      fetchSoulSummary(requestedId),
      fetchMemorySynthesis(requestedId),
    ]);
    snapshot = snap;
    plannerSummary = planner;
    rhythmState = rhythm.state;
    rhythmCurve = rhythm.curve;
    soulSummary = soul;
    memorySynthesis = synthesisBundle;
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : 'Unknown error';
  }

  const layerCards: PersonalModelLayerCard[] = snapshot
    ? buildPersonalModelLayers({ snapshot, plannerSummary, rhythmState, soulSummary, memoryBundle: memorySynthesis })
    : [];

  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <header style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <p style={{ textTransform: 'uppercase', letterSpacing: '0.07em', fontSize: '0.85rem', color: '#FB7185' }}>Debug Studio</p>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, lineHeight: 1.2 }}>Person Snapshot</h1>
        <p style={{ maxWidth: '720px', color: '#5C554E' }}>
          Quick, human-readable overview of the selected person: recent journals, short-term memory items, episodic storage, and personal model layers. Use this as a
          living dossier when validating the new ingestion + memory pipelines.
        </p>
        <PersonSnapshotForm initialPersonId={requestedId} />
      </header>

      {errorMessage ? (
        <section style={cardStyle}>
          <h2 style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>Unable to load snapshot</h2>
          <p style={{ color: '#B91C1C' }}>{errorMessage}</p>
        </section>
      ) : (
        snapshot && (
          <>
            <section style={cardStyle}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Recent Journal Entries</h2>
              {snapshot.journals.length === 0 ? (
                <p style={{ color: '#78716C' }}>No recent journals found.</p>
              ) : (
                <ul style={{ display: 'grid', gap: '0.85rem' }}>
                  {snapshot.journals.map((entry) => (
                    <li key={entry.id} style={{ background: 'rgba(254, 243, 199, 0.45)', borderRadius: '16px', padding: '0.85rem 1rem', border: '1px solid rgba(249,115,22,0.18)' }}>
                      <p style={{ fontSize: '0.85rem', color: '#854d0e', marginBottom: '0.35rem' }}>
                        {formatTimestamp(entry.created_at)} • {toDisplay(entry.layer || 'conversation')}
                      </p>
                      <p style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>{toDisplay(entry.text) || '— no text stored —'}</p>
                      <p style={{ fontSize: '0.85rem', color: '#a16207' }}>
                        {entry.mood ? `Mood: ${toDisplay(entry.mood)}` : 'Mood: n/a'}
                        {entry.tags && entry.tags.length > 0 ? ` • Tags: ${entry.tags.map(toDisplay).join(', ')}` : ''}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section style={cardStyle}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Short-Term Memory Window</h2>
              {snapshot.short_term_memory.length === 0 ? (
                <p style={{ color: '#78716C' }}>No short-term memory entries recorded yet.</p>
              ) : (
                <ul style={{ display: 'grid', gap: '0.75rem' }}>
                  {snapshot.short_term_memory.map((memory) => (
                    <li key={memory.id} style={{ padding: '0.75rem 0.85rem', borderRadius: '14px', background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(14,116,144,0.25)' }}>
                      <p style={{ fontSize: '0.85rem', color: '#0f766e', marginBottom: '0.35rem' }}>{formatTimestamp(memory.created_at)}</p>
                      <p style={{ fontWeight: 500, marginBottom: '0.25rem' }}>{toDisplay(memory.text) || 'No text captured for this memory.'}</p>
                      {memory.tags && memory.tags.length > 0 && <p style={{ fontSize: '0.85rem', color: '#0e7490' }}>Tags: {memory.tags.map(toDisplay).join(', ')}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section style={cardStyle}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.75rem' }}>Episodic Memory (Worker Output)</h2>
              {snapshot.episodic_memory.length === 0 ? (
                <p style={{ color: '#78716C' }}>No episodic rows stored yet.</p>
              ) : (
                <div style={{ display: 'grid', gap: '0.75rem' }}>
                  {snapshot.episodic_memory.map((episode) => (
                    <article key={episode.id} style={{ padding: '0.85rem 1rem', border: '1px solid rgba(59,130,246,0.25)', borderRadius: '16px', background: 'rgba(191,219,254,0.35)' }}>
                      <p style={{ fontSize: '0.85rem', color: '#1d4ed8', marginBottom: '0.35rem' }}>
                        {formatTimestamp(episode.created_at)} • {toDisplay(episode.layer || 'episode')}
                      </p>
                      <p style={{ marginBottom: '0.25rem' }}>{toDisplay(episode.text) || 'No stored summary.'}</p>
                      {episode.tags && episode.tags.length > 0 && <p style={{ fontSize: '0.85rem', color: '#1d4ed8' }}>Tags: {episode.tags.map(toDisplay).join(', ')}</p>}
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section style={cardStyle}>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Personal Model Layers</h2>
              <p style={{ color: '#6b4f3f', marginBottom: '1rem' }}>
                Last updated {snapshot.personal_model.updated_at ? formatTimestamp(snapshot.personal_model.updated_at) : 'recently'} • Highlights below combine short-term signals
                with the slow-moving long-term persona.
              </p>
              {layerCards.length > 0 ? (
                <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))' }}>
                  {layerCards.map((card) => (
                    <div key={card.key} style={{ borderRadius: '16px', padding: '0.85rem 1rem', border: '1px solid rgba(107,114,128,0.25)', background: 'rgba(243,244,246,0.8)' }}>
                      <p style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.35rem' }}>{card.label}</p>
                      <p style={{ fontSize: '0.9rem', color: '#4b5563' }}>{card.summary || 'No summary stored yet.'}</p>
                      <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.4rem' }}>{card.confidence}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#78716C' }}>No personal model layers recorded yet.</p>
              )}
            </section>

            {snapshot.latest_prompt && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Latest Conversation Prompt</h2>
                {snapshot.latest_prompt.error ? (
                  <p style={{ color: '#B91C1C' }}>{snapshot.latest_prompt.error}</p>
                ) : (
                  <div style={{ display: 'grid', gap: '0.9rem' }}>
                    <div>
                      <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#5C554E', marginBottom: '0.25rem' }}>User Text</p>
                      <pre style={{ whiteSpace: 'pre-wrap', margin: 0, background: 'rgba(248,250,252,0.9)', padding: '0.75rem', borderRadius: '12px', fontSize: '0.95rem' }}>
                        {toDisplay(snapshot.latest_prompt.user_text) || 'n/a'}
                      </pre>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#5C554E', marginBottom: '0.25rem' }}>Prompt sent to LLM</p>
                      <pre style={{ whiteSpace: 'pre-wrap', margin: 0, background: 'rgba(248,250,252,0.9)', padding: '0.75rem', borderRadius: '12px', fontSize: '0.95rem' }}>
                        {toDisplay(snapshot.latest_prompt.prompt) || 'n/a'}
                      </pre>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#5C554E', marginBottom: '0.25rem' }}>System Context</p>
                      <pre style={{ whiteSpace: 'pre-wrap', margin: 0, background: 'rgba(248,250,252,0.9)', padding: '0.75rem', borderRadius: '12px', fontSize: '0.95rem' }}>
                        {toDisplay(snapshot.latest_prompt.system_context) || 'n/a'}
                      </pre>
                    </div>
                  </div>
                )}
              </section>
            )}

            {plannerSummary && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Planner Snapshot (Build 33)</h2>
                <p style={{ color: '#6B7280', marginBottom: '0.75rem' }}>Tasks pulled from /planner/summary including new suggestions and goal alignment.</p>
                <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#FB7185', marginBottom: '0.35rem' }}>Today</h3>
                    {Array.isArray(plannerSummary.today) && plannerSummary.today.length > 0 ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {plannerSummary.today.map((task: any, idx: number) => (
                      <li key={`planner-today-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(254, 243, 199, 0.7)', border: '1px solid rgba(251, 113, 133, 0.15)' }}>
                        <p style={{ fontWeight: 600 }}>{toDisplay(task.label || task.window || 'Task')}</p>
                        <p style={{ fontSize: '0.9rem', color: '#6B7280' }}>
                          {task.due_ts ? formatTimestamp(task.due_ts) : task.energy ? `${toDisplay(task.energy)} energy` : 'Flexible'}
                        </p>
                      </li>
                    ))}
                  </ul>
                ) : (
                      <p style={{ color: '#9CA3AF' }}>No committed tasks for today.</p>
                    )}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#FB7185', marginBottom: '0.35rem' }}>Week</h3>
                    {Array.isArray(plannerSummary.week) && plannerSummary.week.length > 0 ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {plannerSummary.week.map((task: any, idx: number) => (
                      <li key={`planner-week-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(219, 234, 254, 0.6)', border: '1px solid rgba(59, 130, 246, 0.15)' }}>
                        <p style={{ fontWeight: 600 }}>{toDisplay(task.label || task.day || 'Focus')}</p>
                        <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>{task.due_ts ? formatTimestamp(task.due_ts) : toDisplay(task.details || task.focus || 'Scheduled')}</p>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p style={{ color: '#9CA3AF' }}>Week view empty.</p>
                    )}
                  </div>
                </div>
              </section>
            )}

            {plannerSummary?.rhythm_alignment && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Flow Windows (Build 40)</h2>
                <p style={{ color: '#6B7280', marginBottom: '0.75rem' }}>
                  Rhythm × Planner fusion: recommended windows aligned to energy peaks and weekly cadence.
                </p>
                <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
                  {['today', 'week'].map((bucket) => {
                    const block = (plannerSummary as any).rhythm_alignment?.[bucket];
                    const generatedAt = block?.generated_at;
                    const recsSource = block?.recommendations ?? block;
                    const recs = parseRecommendationList(recsSource);
                    return (
                      <div key={bucket} style={{ borderRadius: '14px', border: '1px solid rgba(59,130,246,0.15)', background: 'rgba(219,234,254,0.5)', padding: '0.85rem' }}>
                        <p style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1D4ED8', marginBottom: '0.35rem', textTransform: 'capitalize' }}>
                          {bucket}
                        </p>
                        <p style={{ fontSize: '0.85rem', color: '#6B7280', marginBottom: '0.5rem' }}>
                          {generatedAt ? `Generated ${formatTimestamp(generatedAt)}` : 'Generated recently'}
                        </p>
                        {recs.length ? (
                          <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                            {recs.map((rec: any, idx: number) => (
                              <li key={`${bucket}-rec-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(255,255,255,0.9)', border: '1px solid rgba(59,130,246,0.12)' }}>
                                <p style={{ fontWeight: 600 }}>{toDisplay(rec.window || rec.day || rec.label || 'Window')}</p>
                                <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>
                                  {rec.energy ? `${toDisplay(rec.energy)} energy` : 'Energy n/a'}
                                  {rec.focus ? ` • Focus ${toDisplay(rec.focus)}` : ''}
                                  {rec.fit ? ` • Fits ${Array.isArray(rec.fit) ? rec.fit.map(toDisplay).join(', ') : toDisplay(rec.fit)}` : ''}
                                </p>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p style={{ color: '#9CA3AF' }}>No rhythm-aligned windows yet.</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {(rhythmState || rhythmCurve) && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Rhythm Engine (Build 34)</h2>
                {rhythmState ? (
                  <div style={{ display: 'grid', gap: '0.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: '1rem' }}>
                    <div>
                      <p style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>Energy</p>
                      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{Math.round(Number(rhythmState.body_energy ?? 0) * 100)}%</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>Fatigue</p>
                      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{Math.round(Number(rhythmState.fatigue_level ?? 0) * 100)}%</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>Stress</p>
                      <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>{Math.round(Number(rhythmState.stress_level ?? 0) * 100)}%</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>Chronotype</p>
                      <p style={{ fontSize: '1.1rem', fontWeight: 600, textTransform: 'capitalize' }}>{rhythmState.chronotype || 'intermediate'}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.8rem', color: '#9CA3AF' }}>Next peak / lull</p>
                      <p style={{ fontSize: '0.95rem' }}>
                        {rhythmState.next_peak ? formatTimestamp(rhythmState.next_peak) : 'n/a'} • {rhythmState.next_lull ? formatTimestamp(rhythmState.next_lull) : 'n/a'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p style={{ color: '#9CA3AF', marginBottom: '1rem' }}>No rhythm state recorded yet.</p>
                )}

                {rhythmCurve?.alignment && (
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#FB7185', marginBottom: '0.35rem' }}>Planner Alignment</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {(() => {
                        const raw = rhythmCurve.alignment.today;
                        let todayWindows: any[] = [];
                        if (Array.isArray(raw)) todayWindows = raw;
                        else if (typeof raw === 'string') {
                          try {
                            todayWindows = JSON.parse(raw);
                          } catch {
                            todayWindows = [];
                          }
                        }
                        if (!todayWindows.length) {
                          return <p style={{ color: '#9CA3AF' }}>No rhythm-based suggestions yet.</p>;
                        }
                        return todayWindows.map((rec, idx) => (
                          <div key={`rhythm-align-${idx}`} style={{ borderRadius: '12px', border: '1px solid rgba(59,130,246,0.15)', padding: '0.65rem', background: 'rgba(219,234,254,0.5)' }}>
                            <p style={{ fontWeight: 600 }}>{toDisplay(rec.window || rec.label || 'Window')}</p>
                            <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>
                              {rec.energy ? `${toDisplay(rec.energy)} energy` : '—'} {rec.fit ? `• Fits ${Array.isArray(rec.fit) ? rec.fit.map(toDisplay).join(', ') : toDisplay(rec.fit)}` : ''}
                            </p>
                          </div>
                        ));
                      })()}
                    </div>
                  </div>
                )}
              </section>
            )}

            {soulSummary && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Soul Layer (Build 35)</h2>
                <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))' }}>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#7C3AED', marginBottom: '0.3rem' }}>Values</h3>
                    {Array.isArray(soulSummary.values) && soulSummary.values.length > 0 ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {soulSummary.values.slice(0, 4).map((value: any, idx: number) => (
                  <li key={`value-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(233,213,255,0.55)', border: '1px solid rgba(147,51,234,0.2)' }}>
                    <p style={{ fontWeight: 600 }}>{toDisplay(value.value_name)}</p>
                    <p style={{ fontSize: '0.9rem', color: '#6B7280' }}>{toDisplay(value.description)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#9CA3AF' }}>No values captured yet.</p>
                    )}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#7C3AED', marginBottom: '0.3rem' }}>Identity Signatures</h3>
                    {Array.isArray(soulSummary.identity_signatures) && soulSummary.identity_signatures.length > 0 ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {soulSummary.identity_signatures.map((sig: any, idx: number) => (
                  <li key={`identity-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(219,234,254,0.6)', border: '1px solid rgba(59,130,246,0.15)' }}>
                    <p style={{ fontWeight: 600 }}>{toDisplay(sig.label)}</p>
                    <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>{toDisplay(sig.narrative)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#9CA3AF' }}>No identity statements yet.</p>
                    )}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#7C3AED', marginBottom: '0.3rem' }}>Purpose Themes</h3>
                    {Array.isArray(soulSummary.purpose_themes) && soulSummary.purpose_themes.length > 0 ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {soulSummary.purpose_themes.map((theme: any, idx: number) => (
                  <li key={`theme-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(236,254,255,0.7)', border: '1px solid rgba(59,130,246,0.15)' }}>
                    <p style={{ fontWeight: 600 }}>{toDisplay(theme.theme)}</p>
                    <p style={{ fontSize: '0.9rem', color: '#0F172A' }}>{toDisplay(theme.description)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#9CA3AF' }}>No purpose themes detected.</p>
                    )}
                  </div>
                </div>
                {Array.isArray(soulSummary.life_arcs) && soulSummary.life_arcs.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h3 style={{ fontSize: '1rem', color: '#7C3AED', marginBottom: '0.3rem' }}>Life Arcs</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {soulSummary.life_arcs.map((arc: any, idx: number) => (
                    <div key={`arc-${idx}`} style={{ borderRadius: '12px', border: '1px solid rgba(107,114,128,0.2)', padding: '0.65rem', background: 'rgba(243,244,246,0.85)' }}>
                      <p style={{ fontWeight: 600 }}>{toDisplay(arc.arc_name)}</p>
                      <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>{toDisplay(arc.summary)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
                {Array.isArray(soulSummary.conflicts) && soulSummary.conflicts.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <h3 style={{ fontSize: '1rem', color: '#DC2626', marginBottom: '0.3rem' }}>Conflicts</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {soulSummary.conflicts.map((conflict: any, idx: number) => (
                        <div key={`conflict-${idx}`} style={{ borderRadius: '12px', border: '1px solid rgba(248,113,113,0.25)', padding: '0.65rem', background: 'rgba(254,226,226,0.8)' }}>
                          <p style={{ fontWeight: 600 }}>{toDisplay(conflict.conflict_type)}</p>
                          <p style={{ fontSize: '0.9rem', color: '#7F1D1D' }}>{toDisplay(conflict.description)}</p>
                          <p style={{ fontSize: '0.85rem', color: '#9B2C2C' }}>{toDisplay(conflict.resolution_hint)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}

            {(memorySynthesis.weekly || memorySynthesis.monthly) && (
              <section style={cardStyle}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Memory Synthesis (Build 37)</h2>
                <div style={{ display: 'grid', gap: '1.25rem', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))' }}>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#0EA5E9', marginBottom: '0.35rem' }}>Weekly Reflection</h3>
                    {Array.isArray(memorySynthesis.weekly?.items) && memorySynthesis.weekly?.items.length ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {memorySynthesis.weekly.items.map((item: any, idx: number) => (
                      <li key={`weekly-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(219,234,254,0.6)', border: '1px solid rgba(59,130,246,0.15)' }}>
                        <p style={{ fontWeight: 600 }}>{toDisplay(item.week_start)} → {toDisplay(item.week_end)}</p>
                        <p style={{ fontSize: '0.9rem', color: '#4B5563' }}>{toDisplay(item.highlights) || 'No highlight stored yet.'}</p>
                        <p style={{ fontSize: '0.8rem', color: '#6B7280' }}>
                          Drift {item.drift_score != null ? `${Math.round(Number(item.drift_score) * 100)}%` : 'n/a'}
                        </p>
                      </li>
                    ))}
                      </ul>
                    ) : (
                      <p style={{ color: '#9CA3AF' }}>Weekly synthesis pending.</p>
                    )}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1rem', color: '#0EA5E9', marginBottom: '0.35rem' }}>Monthly Recap</h3>
                    {Array.isArray(memorySynthesis.monthly?.items) && memorySynthesis.monthly?.items.length ? (
                      <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {memorySynthesis.monthly.items.map((item: any, idx: number) => (
                      <li key={`monthly-${idx}`} style={{ padding: '0.65rem', borderRadius: '12px', background: 'rgba(240,249,255,0.7)', border: '1px solid rgba(14,165,233,0.2)' }}>
                        <p style={{ fontWeight: 600 }}>{toDisplay(item.month_scope || `${toDisplay(item.month_start)} → ${toDisplay(item.month_end) || ''}`)}</p>
                        <p style={{ fontSize: '0.9rem', color: '#0F172A' }}>{toDisplay(item.chapter_hint || item.highlights) || 'Monthly chapter pending.'}</p>
                        <p style={{ fontSize: '0.8rem', color: '#0E7490' }}>
                          Drift {item.drift_score != null ? `${Math.round(Number(item.drift_score) * 100)}%` : 'n/a'}
                        </p>
                      </li>
                    ))}
                      </ul>
                    ) : (
                      <p style={{ color: '#9CA3AF' }}>Monthly recap pending.</p>
                    )}
                  </div>
                </div>
              </section>
            )}
          </>
        )
      )}
    </div>
  );
}

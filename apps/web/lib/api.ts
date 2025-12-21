const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

type MemoryObservePayload = {
  person_id: string;
  text: string;
  layer?: string;
  tags?: string[];
  mood?: string | null;
  ts?: string;
};

type ClarityEvaluatePayload = {
  person_id: string;
  user_text: string;
  need?: string;
  horizon?: string;
};

type MemoryObserveResponse = {
  entry_id: string;
  triage?: Record<string, unknown>;
  salience?: number;
  debug?: any;
  personal_model?: Record<string, unknown>;
  web?: {
    query: string;
    snippet: string;
    entry_id?: string;
  };
};

type ClarityEvaluateResponse = {
  context: Record<string, unknown>;
  impact_panel?: Record<string, unknown>;
  options?: any[];
  score?: number;
  debug?: any;
  phrase?: any;
  person_summary?: any;
  insight_id?: string;
  personal_model?: Record<string, unknown>;
};

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  });

  const text = await response.text();
  let data: any = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: text };
    }
  }

  if (!response.ok) {
    const detail = typeof data?.error === 'string' ? data.error : response.statusText;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return data as T;
}

export const api = {
  memory: {
    observe: (payload: MemoryObservePayload) =>
      postJson<MemoryObserveResponse>('/api/memory/observe', payload),
  },
  clarity: {
    evaluate: (payload: ClarityEvaluatePayload) =>
      postJson<ClarityEvaluateResponse>('/api/clarity/evaluate', payload),
  },
  turn: {
    v2: (payload: { text: string; clarity_phrase?: string | null }) =>
      postJson<any>('/api/turn-v2', payload),
  },
  person: {
    goalUpsert: (payload: { person_id: string; title: string; status?: string; horizon?: string; progress?: number }) =>
      postJson<{ ok: boolean; id?: string }>('/api/person/goal/upsert', payload),
    preferenceUpsert: (payload: { person_id: string; scope: string; key: string; value: Record<string, unknown>; confidence?: number }) =>
      postJson<{ ok: boolean }>('/api/person/preference/upsert', payload),
  },
  async post<T = any>(url: string, payload: unknown): Promise<{ data: T; status: number }> {
    const response = await fetch(`${API_BASE}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include',
    });

    const text = await response.text();
    let data: any = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }

    if (!response.ok) {
      console.error('API POST failed', url, response.status, data);
      throw new Error(typeof data === 'string' ? data : `Request failed with status ${response.status}`);
    }

    return { data, status: response.status };
  },
};

export async function addEntry(content: string, accessToken?: string): Promise<void> {
  const response = await fetch(`${API_BASE}/journal/turn`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({ text: content }),
    credentials: 'include',
  });

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText);
    throw new Error(message || `Request failed with status ${response.status}`);
  }
}

export async function fetchPersonSummary(person_id: string, short_days = 7, long_days = 90) {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    console.error('Missing NEXT_PUBLIC_API_URL');
    return null;
  }

  const response = await fetch(`${base}/person/summary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ person_id, short_days, long_days }),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => response.statusText);
    console.error('person/summary failed', response.status, body);
    return null;
  }

  return response.json();
}

export async function fetchPersonModel(person_id: string) {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    console.error('Missing NEXT_PUBLIC_API_URL');
    return null;
  }

  const url = new URL('/person/model', base);
  url.searchParams.set('person_id', person_id);

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const body = await response.text().catch(() => response.statusText);
    console.error('person/model failed', response.status, body);
    return null;
  }

  return response.json();
}

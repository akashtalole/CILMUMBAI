// Typed calls to the query API (SPEC-007) and the ask endpoint. Same origin in production; proxied in development.

export type Tier = "official" | "reported" | "citizen" | "derived";

export interface GraphNode {
  id: string;
  label: string;
  fact_id?: string;
  source?: string;
  page?: number;
  quote?: string | null;
  tier?: Tier;
  name?: string;
  name_mr?: string;
  title?: string;
  code?: string;
  [key: string]: unknown;
}

export interface Gap {
  hop: string;
  record_needed: string;
  holder: string;
}

export interface Row {
  hop: string;
  node?: GraphNode;
  work?: GraphNode;
  period?: GraphNode;
  contractor?: GraphNode | null;
  hops?: Row[];
  work_id?: string;
  steps?: number;
}

export interface ViewResult {
  rows: Row[];
  gaps: Gap[];
}

export interface Place {
  node_id: string;
  kind: "Road" | "AdminWard" | "ElectoralWard";
  name: string;
  matched: string;
  segments: number;
}

export interface PointResult {
  road: { node_id: string; name: string; name_mr?: string; distance_m: number } | null;
  admin_ward: { node_id: string; code: string; name: string } | null;
  note: string;
}

export interface SourceInfo {
  fact_id: string;
  document: string;
  page: number;
  quote: string;
  publisher: string;
}

export interface Answer {
  text: string;
  body: string;
  language: string;
  status: "answered" | "asked_location" | "fallback";
  sources: SourceInfo[];
  draft_letter: string | null;
  gaps: Gap[];
}

export interface AskJob {
  id: string;
  status: "running" | "done" | "failed";
  elapsed_s: number;
  answer?: Answer;
  error?: string;
}

export interface SourcePage {
  publisher: string;
  licence: string;
  page_count: number;
  fetched_at: string | null;
}

export interface SavedArea {
  id: number;
  kind: "point" | "roads";
  lat: number | null;
  lon: number | null;
  radius_m: number | null;
  road_ids: string[];
  language: string;
  created_at: string;
}

export interface Alert {
  id: number;
  created_at: string;
  kind: string;
  text: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, String(detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  places: (q: string) => call<Place[]>(`/places?q=${encodeURIComponent(q)}`),
  point: (lat: number, lon: number) => call<PointResult>(`/point?lat=${lat}&lon=${lon}`),
  shape: (id: string) => call<GeoJSON.Feature>(`/places/${encodeURIComponent(id)}/shape`),
  responsible: (id: string, issue: string) =>
    call<ViewResult>(`/views/who_is_responsible?id=${encodeURIComponent(id)}&issue=${encodeURIComponent(issue)}`),
  money: (id: string) => call<ViewResult>(`/views/trace_money?id=${encodeURIComponent(id)}`),
  source: (sha: string, page: number) => call<SourcePage>(`/sources/${sha}/pages/${page}`),
  ask: (question: string, language: string, location?: { lat: number; lon: number }) =>
    call<{ id: string }>(`/ask`, {
      method: "POST",
      body: JSON.stringify({ question, language, ...(location ?? {}) }),
    }),
  askStatus: (id: string) => call<AskJob>(`/ask/${id}`),
  // Saved areas and alerts belong to an account (SPEC-010). Until sign-in exists, the token is an access code.
  areas: (token: string) => call<SavedArea[]>(`/subscriptions`, { headers: auth(token) }),
  saveArea: (token: string, area: Record<string, unknown>) =>
    call<SavedArea>(`/subscriptions`, { method: "POST", headers: auth(token), body: JSON.stringify(area) }),
  removeArea: (token: string, id: number) =>
    fetch(`/subscriptions/${id}`, { method: "DELETE", headers: auth(token) }).then((r) => {
      if (!r.ok) throw new ApiError(r.status, r.statusText);
    }),
  alerts: (token: string) => call<Alert[]>(`/alerts`, { headers: auth(token) }),
};

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

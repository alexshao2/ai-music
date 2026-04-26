export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Brief = {
  mood: string;
  genre: string;
  language: string;
  duration_sec: number;
  references: string[];
  notes?: string | null;
};

export type CouncilTurn = {
  persona: string;
  role: string;
  message: string;
};

export type Section = {
  section: string;
  bars: number;
  chords: string[];
  notes?: string | null;
};

export type SongDraft = {
  id: string;
  title: string;
  brief: Brief;
  key: string;
  tempo_bpm: number;
  structure: Section[];
  lyrics: Record<string, string>;
  arrangement: Record<string, unknown>;
  production: Record<string, unknown>;
  council_log: CouncilTurn[];
  suno_prompt?: { style: string; lyrics: string; title: string } | null;
};

export type KnowledgeChunk = {
  path: string;
  title: string;
  tags: string[];
  level?: string | null;
  excerpt: string;
  score: number;
};

export type Persona = {
  name: string;
  role: string;
  expertise_tags: string[];
  system_prompt: string;
};

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  personas: () => http<Persona[]>("/council/personas"),
  briefIntake: (b: Brief) =>
    http<{ brief: Brief; clarifying_questions: string[] }>("/council/brief", {
      method: "POST",
      body: JSON.stringify(b),
    }),
  compose: (b: Brief, opts?: { fast?: boolean }) =>
    http<SongDraft>(
      `/council/compose${opts?.fast ? "?fast=true" : ""}`,
      {
        method: "POST",
        body: JSON.stringify(b),
      },
    ),
  drafts: () => http<SongDraft[]>("/studio/drafts"),
  draft: (id: string) => http<SongDraft>(`/studio/drafts/${id}`),
  knowledgeTopics: () => http<KnowledgeChunk[]>("/knowledge/topics"),
  knowledgeSearch: (q: string) =>
    http<KnowledgeChunk[]>(
      `/knowledge/search?q=${encodeURIComponent(q)}&k=8`,
    ),
  sunoLaunch: (id: string) =>
    http<{
      open_url: string;
      title: string;
      style: string;
      lyrics: string;
    }>(`/suno/launch/${id}`),
  sunoAutofill: (id: string, opts?: { wait?: boolean; timeoutSec?: number }) =>
    http<{
      submitted: boolean;
      title: string;
      style: string;
      lyrics_chars: number;
      suno_url: string | null;
      note: string | null;
    }>(
      `/suno/autofill/${id}?wait=${opts?.wait ?? true}` +
        (opts?.timeoutSec ? `&timeout_sec=${opts.timeoutSec}` : ""),
      { method: "POST" },
    ),
};

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

export type SunoOutput = {
  title: string;
  style: string;
  lyrics: string;
  negative_tags: string[];
  producer_brief: string;
};

export type SongDraft = {
  id: string;
  title: string;
  brief: Brief;
  key: string;
  tempo_bpm: number;
  structure: Section[];
  lyrics: Record<string, string>;
  lyrics_with_markers: Record<string, string>;
  arrangement: Record<string, unknown>;
  production: Record<string, unknown>;
  council_log: CouncilTurn[];
  suno_prompt?: { style: string; lyrics: string; title: string } | null;
  suno_output?: SunoOutput | null;
  compliance: Record<string, boolean>;
  evaluation?: QualityEvaluation | null;
};

export type QualityScores = {
  melody_catchiness: number;
  lyric_quality: number;
  harmonic_sophistication: number;
  structural_coherence: number;
  production_direction: number;
  genre_authenticity: number;
  overall: number;
};

export type QualityEvaluation = {
  scores: QualityScores;
  verdict: "RELEASE" | "REVISE" | "REJECT";
  feedback: string;
  revision_notes: string;
  attempt: number;
  max_attempts_reached: boolean;
};

export type PromptValidation = {
  valid: boolean;
  score: number;
  issues: string[];
  suggestions: string[];
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

// Brief picker option shapes — served by GET /council/options. Genres are
// generated from knowledge/genres/*.md frontmatter so new cookbooks appear
// in the UI automatically. Moods are curated in the backend module
// app.services.options.
export type GenreOption = {
  slug: string;
  label: string;
  group: string;
  group_label: string;
  tags: string[];
  knowledge_path: string;
};

export type MoodOption = {
  slug: string;
  label: string;
  group: string;
  keywords: string[];
};

export type LanguageOption = {
  code: string;
  label: string;
};

export type BriefOptions = {
  genres: GenreOption[];
  moods: MoodOption[];
  languages: LanguageOption[];
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
  briefOptions: () => http<BriefOptions>("/council/options"),
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
      negative_tags?: string[];
      producer_brief?: string;
    }>(`/suno/launch/${id}`),
  composeQuality: (
    b: Brief,
    opts?: { targetScore?: number; maxRevisions?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.targetScore != null) params.set("target_score", String(opts.targetScore));
    if (opts?.maxRevisions != null) params.set("max_revisions", String(opts.maxRevisions));
    const qs = params.toString();
    return http<SongDraft>(
      `/council/compose/quality${qs ? `?${qs}` : ""}`,
      { method: "POST", body: JSON.stringify(b) },
    );
  },
  evaluateDraft: (id: string) =>
    http<QualityEvaluation>(`/studio/drafts/${id}/evaluate`, {
      method: "POST",
    }),
  draftQuality: (id: string) =>
    http<QualityEvaluation>(`/studio/drafts/${id}/quality`),
  validatePrompt: (id: string) =>
    http<PromptValidation>(`/studio/drafts/${id}/validate-prompt`, {
      method: "POST",
    }),
};

// ---- Streaming compose ----

export type CouncilStreamEvent =
  | {
      type: "persona_started";
      role: string;
      name: string;
      index: number;
      total: number;
    }
  | {
      type: "persona_completed";
      role: string;
      name: string;
      message: string;
      contributions: Record<string, unknown>;
    }
  | { type: "persona_failed"; role: string; name: string; error: string }
  | { type: "refine_started"; role: string; name: string }
  | {
      type: "refine_completed";
      role: string;
      name: string;
      message: string;
      contributions: Record<string, unknown>;
    }
  | { type: "refine_failed"; role: string; name: string; error: string }
  | {
      type: "revision_started";
      attempt: number;
      max_attempts: number;
      target_score: number;
      brief_notes: string;
    }
  | {
      type: "revision_completed";
      attempt: number;
      score: number;
      verdict: "RELEASE" | "REVISE" | "REJECT";
      passed: boolean;
      revision_brief: string;
    }
  | { type: "revision_failed"; attempt: number; error: string }
  | { type: "draft"; draft: SongDraft; best_attempt?: number }
  | { type: "error"; message: string }
  | { type: "done" };

/** Per-event ``attempt`` field — present on every event yielded by the
 *  quality-stream variant so the UI can group council turns by revision
 *  attempt. ``CouncilStreamEvent`` keeps the field optional so the plain
 *  ``composeStream`` path doesn't have to set it. */
export type CouncilStreamEventWithAttempt = CouncilStreamEvent & {
  attempt?: number;
};

async function _readSSE(
  url: string,
  brief: Brief,
  signal: AbortSignal | undefined,
  onEvent: (event: CouncilStreamEventWithAttempt) => void,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "text/event-stream",
    },
    body: JSON.stringify(brief),
    signal,
    cache: "no-store",
  });
  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${text}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  // SSE frames are separated by a blank line. Parse incrementally so events
  // surface to the UI the moment they arrive, not at the end of the stream.
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of block.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        try {
          onEvent(
            JSON.parse(line.slice(6)) as CouncilStreamEventWithAttempt,
          );
        } catch (err) {
          console.warn("compose stream: bad JSON", line, err);
        }
      }
    }
  }
}

export async function composeStream(
  brief: Brief,
  opts: { fast?: boolean; signal?: AbortSignal },
  onEvent: (event: CouncilStreamEvent) => void,
): Promise<void> {
  const url = `${API_BASE}/council/compose/stream${
    opts.fast ? "?fast=true" : ""
  }`;
  await _readSSE(url, brief, opts.signal, (e) => onEvent(e));
}

export async function composeQualityStream(
  brief: Brief,
  opts: {
    fast?: boolean;
    targetScore?: number;
    maxRevisions?: number;
    signal?: AbortSignal;
  },
  onEvent: (event: CouncilStreamEventWithAttempt) => void,
): Promise<void> {
  const params = new URLSearchParams();
  if (opts.fast) params.set("fast", "true");
  if (opts.targetScore != null)
    params.set("target_score", String(opts.targetScore));
  if (opts.maxRevisions != null)
    params.set("max_revisions", String(opts.maxRevisions));
  const qs = params.toString();
  const url = `${API_BASE}/council/compose/quality/stream${
    qs ? `?${qs}` : ""
  }`;
  await _readSSE(url, brief, opts.signal, onEvent);
}

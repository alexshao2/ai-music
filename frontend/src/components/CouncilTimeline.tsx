"use client";

import type { CouncilStreamEventWithAttempt } from "@/lib/api";

export type PersonaState = {
  role: string;
  name: string;
  status: "pending" | "speaking" | "done" | "failed";
  message?: string;
  isRefine?: boolean;
};

export type CouncilAttempt = {
  /** 1-indexed attempt number; matches the SSE ``attempt`` field. */
  attempt: number;
  states: Record<string, PersonaState>;
  refineStates: Record<string, PersonaState>;
  /** Critic's overall score from this attempt. ``undefined`` until Critic
   *  finishes and the backend emits ``revision_completed``. */
  score?: number;
  verdict?: "RELEASE" | "REVISE" | "REJECT";
  passed?: boolean;
  /** ``revision_brief`` from Critic — what the next attempt should fix. */
  revisionBrief?: string;
  targetScore?: number;
  /** Total attempts the gate is willing to run (carried from the
   *  ``revision_started`` event so we can tell intermediate failures apart
   *  from the terminal one without guessing from list length). */
  maxAttempts?: number;
};

/** True only on the final attempt of a quality run that did NOT pass. Used
 *  to render the "HẾT LƯỢT" badge instead of "CHƯA ĐẠT — sẽ sửa" for
 *  intermediate failed attempts. */
function isExhausted(a: CouncilAttempt): boolean {
  return (
    a.passed === false
    && a.maxAttempts != null
    && a.attempt >= a.maxAttempts
  );
}

const ROLE_ORDER = [
  "theorist",
  "composer",
  "lyricist",
  "arranger",
  "producer",
  "critic",
] as const;

const ROLE_DISPLAY: Record<string, string> = {
  theorist: "Music Theorist",
  composer: "Composer",
  lyricist: "Lyricist",
  arranger: "Arranger",
  producer: "Producer",
  critic: "A&R Critic",
};

function statusLabel(s: PersonaState["status"]): string {
  switch (s) {
    case "pending":
      return "Đang chờ tới lượt";
    case "speaking":
      return "Đang phát biểu…";
    case "done":
      return "Đã xong";
    case "failed":
      return "Lỗi";
  }
}

function statusBadge(s: PersonaState["status"]): string {
  switch (s) {
    case "pending":
      return "bg-white/10 text-white/60";
    case "speaking":
      return "bg-atelier text-ink shadow-bloom-soft";
    case "done":
      return "bg-emerald-500/20 text-emerald-300";
    case "failed":
      return "bg-red-500/20 text-red-300";
  }
}

function nodeRing(s: PersonaState["status"]): string {
  switch (s) {
    case "pending":
      return "border-white/15 bg-white/[0.03]";
    case "speaking":
      return "border-magenta/60 bg-magenta/10 shadow-bloom animate-pulse-glow";
    case "done":
      return "border-emerald-400/40 bg-emerald-500/[0.06]";
    case "failed":
      return "border-red-400/50 bg-red-500/[0.06]";
  }
}

function AttemptBlock({
  attempt,
  showHeader,
}: {
  attempt: CouncilAttempt;
  showHeader: boolean;
}) {
  const headerBadge = (() => {
    if (attempt.passed === true) {
      return {
        label: `ĐẠT ${attempt.score?.toFixed(1)} / ${attempt.targetScore?.toFixed(1) ?? "?"}`,
        cls: "bg-emerald-500/20 text-emerald-300",
      };
    }
    if (attempt.passed === false && isExhausted(attempt)) {
      return {
        label: `HẾT LƯỢT — best ${attempt.score?.toFixed(1) ?? "?"}`,
        cls: "bg-amber-500/20 text-amber-300",
      };
    }
    if (attempt.passed === false) {
      return {
        label: `CHƯA ĐẠT ${attempt.score?.toFixed(1) ?? "?"} — sẽ sửa`,
        cls: "bg-orange-500/20 text-orange-300",
      };
    }
    return {
      label: "Đang chạy…",
      cls: "bg-atelier text-ink shadow-bloom-soft",
    };
  })();

  return (
    <div className="rounded-lg border border-white/10 bg-ink/40 p-4 space-y-3">
      {showHeader && (
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-gold">
            ── Vòng {String(attempt.attempt).padStart(2, "0")}
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] ${headerBadge.cls}`}
          >
            {headerBadge.label}
          </span>
        </div>
      )}
      {attempt.revisionBrief && (
        <p className="text-xs italic text-amber-200/80 border-l-2 border-amber-300/40 pl-2">
          Critic yêu cầu sửa: {attempt.revisionBrief}
        </p>
      )}
      <ul className="space-y-2">
        {ROLE_ORDER.map((role) => {
          const state = attempt.states[role] ?? {
            role,
            name: ROLE_DISPLAY[role],
            status: "pending" as const,
          };
          const refine = attempt.refineStates[role];
          return (
            <li
              key={role}
              className={`rounded-md border p-3 transition-colors ${nodeRing(state.status)}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-medium text-white">
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/45">
                    {String(ROLE_ORDER.indexOf(role) + 1).padStart(2, "0")}
                  </span>
                  {state.name ?? ROLE_DISPLAY[role]}
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/40">
                    {role}
                  </span>
                </div>
                <span
                  className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] ${statusBadge(state.status)}`}
                >
                  {statusLabel(state.status)}
                </span>
              </div>
              {state.message && (
                <p className="mt-2 text-sm text-white/85 whitespace-pre-wrap">
                  {state.message}
                </p>
              )}
              {refine && (
                <div className="mt-3 rounded-md border border-accent/20 bg-accent/5 p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-accent/80 uppercase tracking-wide">
                      Tinh chỉnh sau Critic
                    </span>
                    <span
                      className={`text-[11px] uppercase tracking-wide rounded px-2 py-0.5 ${statusBadge(refine.status)}`}
                    >
                      {statusLabel(refine.status)}
                    </span>
                  </div>
                  {refine.message && (
                    <p className="mt-2 text-sm text-white/80 whitespace-pre-wrap">
                      {refine.message}
                    </p>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function CouncilTimeline({
  attempts,
  elapsedSec,
}: {
  attempts: CouncilAttempt[];
  elapsedSec: number;
}) {
  const showAttemptHeaders = attempts.length > 1 || attempts.some(
    (a) => a.passed != null,
  );
  return (
    <div className="card card-glow p-5 space-y-4">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="chip-mono">live · sse stream</p>
          <h3 className="mt-2 font-display text-2xl tracking-tight">
            Hội đồng <span className="text-atelier">đang họp</span>
          </h3>
        </div>
        <span className="font-mono text-xs uppercase tracking-[0.2em] text-white/55">
          ⏱ {formatElapsed(elapsedSec)}
        </span>
      </div>
      <div className="space-y-3">
        {attempts.map((a) => (
          <AttemptBlock
            key={a.attempt}
            attempt={a}
            showHeader={showAttemptHeaders}
          />
        ))}
      </div>
    </div>
  );
}

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function emptyAttempt(
  attempt: number,
  targetScore?: number,
  maxAttempts?: number,
): CouncilAttempt {
  return {
    attempt,
    states: {},
    refineStates: {},
    targetScore,
    maxAttempts,
  };
}

/** Apply a single SSE event to the running list of attempts.
 *
 *  - For ``compose/stream`` (no quality gate), every event lands in attempt 1
 *    and we never push a second attempt. The caller seeds the list with one
 *    empty attempt before the stream starts.
 *  - For ``compose/quality/stream``, ``revision_started`` pushes a new
 *    attempt; persona/refine events are routed to the attempt named on the
 *    event (or the last one if missing); ``revision_completed`` stamps score
 *    + verdict on that attempt.
 */
export function applyEvent(
  prev: CouncilAttempt[],
  ev: CouncilStreamEventWithAttempt,
): CouncilAttempt[] {
  const attempts = prev.length > 0 ? [...prev] : [emptyAttempt(1)];

  function patchAttempt(attemptNo: number | undefined, fn: (a: CouncilAttempt) => CouncilAttempt) {
    const target = attemptNo ?? attempts[attempts.length - 1].attempt;
    const idx = attempts.findIndex((a) => a.attempt === target);
    if (idx === -1) {
      // Event arrived before its revision_started — create a placeholder.
      attempts.push(fn(emptyAttempt(target)));
      return;
    }
    attempts[idx] = fn(attempts[idx]);
  }

  switch (ev.type) {
    case "revision_started": {
      const existing = attempts.findIndex((a) => a.attempt === ev.attempt);
      if (existing === -1) {
        attempts.push(
          emptyAttempt(ev.attempt, ev.target_score, ev.max_attempts),
        );
      } else {
        attempts[existing] = {
          ...attempts[existing],
          targetScore: ev.target_score,
          maxAttempts: ev.max_attempts,
        };
      }
      break;
    }
    case "revision_completed":
      // Don't compute the "exhausted" badge here — we don't yet know if a
      // ``revision_started`` for attempt N+1 is coming. ``isExhausted()``
      // derives it on render from ``maxAttempts`` carried by
      // ``revision_started``.
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        score: ev.score,
        verdict: ev.verdict,
        passed: ev.passed,
        revisionBrief: ev.revision_brief,
      }));
      break;
    case "revision_failed":
      // Treat a hard failure as a terminal attempt: clamp ``maxAttempts`` to
      // the current attempt so ``isExhausted`` returns true even if no
      // ``revision_started`` for the next attempt arrives.
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        passed: false,
        maxAttempts: ev.attempt,
      }));
      break;
    case "persona_started":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        states: {
          ...a.states,
          [ev.role]: { role: ev.role, name: ev.name, status: "speaking" },
        },
      }));
      break;
    case "persona_completed":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        states: {
          ...a.states,
          [ev.role]: {
            role: ev.role,
            name: ev.name,
            status: "done",
            message: ev.message,
          },
        },
      }));
      break;
    case "persona_failed":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        states: {
          ...a.states,
          [ev.role]: {
            role: ev.role,
            name: ev.name,
            status: "failed",
            message: "LLM thất bại sau retry — dùng mặc định để hội đồng tiếp tục.",
          },
        },
      }));
      break;
    case "refine_started":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        refineStates: {
          ...a.refineStates,
          [ev.role]: {
            role: ev.role,
            name: ev.name,
            status: "speaking",
            isRefine: true,
          },
        },
      }));
      break;
    case "refine_completed":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        refineStates: {
          ...a.refineStates,
          [ev.role]: {
            role: ev.role,
            name: ev.name,
            status: "done",
            message: ev.message,
            isRefine: true,
          },
        },
      }));
      break;
    case "refine_failed":
      patchAttempt(ev.attempt, (a) => ({
        ...a,
        refineStates: {
          ...a.refineStates,
          [ev.role]: {
            role: ev.role,
            name: ev.name,
            status: "failed",
            isRefine: true,
          },
        },
      }));
      break;
    default:
      break;
  }
  return attempts;
}

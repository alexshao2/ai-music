"use client";

import type { CouncilStreamEvent } from "@/lib/api";

export type PersonaState = {
  role: string;
  name: string;
  status: "pending" | "speaking" | "done" | "failed";
  message?: string;
  isRefine?: boolean;
};

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
      return "bg-accent/30 text-accent animate-pulse";
    case "done":
      return "bg-emerald-500/20 text-emerald-300";
    case "failed":
      return "bg-red-500/20 text-red-300";
  }
}

export function CouncilTimeline({
  states,
  refineStates,
  elapsedSec,
}: {
  states: Record<string, PersonaState>;
  refineStates: Record<string, PersonaState>;
  elapsedSec: number;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-plum/30 p-4 space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-xl text-gold">Hội đồng đang họp</h3>
        <span className="text-xs text-white/50 font-mono">
          {formatElapsed(elapsedSec)}
        </span>
      </div>

      <ul className="space-y-2">
        {ROLE_ORDER.map((role) => {
          const state = states[role] ?? {
            role,
            name: ROLE_DISPLAY[role],
            status: "pending" as const,
          };
          const refine = refineStates[role];
          return (
            <li
              key={role}
              className="rounded-lg border border-white/10 bg-white/5 p-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-accent">
                  {state.name ?? ROLE_DISPLAY[role]}
                  <span className="text-white/40 text-xs ml-2">
                    ({role})
                  </span>
                </div>
                <span
                  className={`text-[11px] uppercase tracking-wide rounded px-2 py-0.5 ${statusBadge(state.status)}`}
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

function formatElapsed(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function applyEvent(
  prevStates: Record<string, PersonaState>,
  prevRefine: Record<string, PersonaState>,
  ev: CouncilStreamEvent,
): {
  states: Record<string, PersonaState>;
  refineStates: Record<string, PersonaState>;
} {
  const states = { ...prevStates };
  const refineStates = { ...prevRefine };
  switch (ev.type) {
    case "persona_started":
      states[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "speaking",
      };
      break;
    case "persona_completed":
      states[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "done",
        message: ev.message,
      };
      break;
    case "persona_failed":
      states[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "failed",
        message: `LLM thất bại sau retry — dùng mặc định để hội đồng tiếp tục.`,
      };
      break;
    case "refine_started":
      refineStates[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "speaking",
        isRefine: true,
      };
      break;
    case "refine_completed":
      refineStates[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "done",
        message: ev.message,
        isRefine: true,
      };
      break;
    case "refine_failed":
      refineStates[ev.role] = {
        role: ev.role,
        name: ev.name,
        status: "failed",
        isRefine: true,
      };
      break;
    default:
      break;
  }
  return { states, refineStates };
}

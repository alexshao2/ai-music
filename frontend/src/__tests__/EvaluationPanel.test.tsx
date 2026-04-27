import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EvaluationPanel } from "@/components/EvaluationPanel";
import type { QualityEvaluation, SongDraft } from "@/lib/api";

const mockEvaluation: QualityEvaluation = {
  scores: {
    melody_catchiness: 8,
    lyric_quality: 7,
    harmonic_sophistication: 6,
    structural_coherence: 7,
    production_direction: 8,
    genre_authenticity: 9,
    overall: 7.6,
  },
  verdict: "RELEASE",
  feedback: "Bài hát rất tốt.",
  revision_notes: "",
  attempt: 1,
  max_attempts_reached: false,
};

function makeDraft(overrides: Partial<SongDraft> = {}): SongDraft {
  return {
    id: "test-001",
    title: "Test Song",
    brief: { mood: "vui", genre: "pop", language: "vi", duration_sec: 180, references: [] },
    key: "C major",
    tempo_bpm: 120,
    structure: [{ section: "verse", bars: 8, chords: ["C", "G"] }],
    lyrics: { verse: "Hello world" },
    lyrics_with_markers: {},
    arrangement: {},
    production: {},
    council_log: [],
    compliance: {},
    evaluation: null,
    ...overrides,
  } as SongDraft;
}

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      evaluateDraft: vi.fn(),
    },
  };
});

describe("EvaluationPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without evaluation — shows run button", () => {
    render(<EvaluationPanel draft={makeDraft()} />);
    expect(screen.getByText("Chạy đánh giá A&R")).toBeInTheDocument();
    expect(screen.getByText("Đánh giá chất lượng")).toBeInTheDocument();
  });

  it("renders with existing evaluation — shows scores and badge", () => {
    render(
      <EvaluationPanel draft={makeDraft({ evaluation: mockEvaluation })} />,
    );
    expect(screen.getByText("Đánh giá lại")).toBeInTheDocument();
    expect(screen.getByText("7.6/10")).toBeInTheDocument();
    expect(screen.getByText("Bài hát rất tốt.")).toBeInTheDocument();
  });

  it("shows all 6 dimension labels", () => {
    render(
      <EvaluationPanel draft={makeDraft({ evaluation: mockEvaluation })} />,
    );
    expect(screen.getByText(/Melody & Hook/)).toBeInTheDocument();
    expect(screen.getByText(/Chất lượng lời/)).toBeInTheDocument();
    expect(screen.getByText(/Hoà âm/)).toBeInTheDocument();
    expect(screen.getByText(/Cấu trúc/)).toBeInTheDocument();
    expect(screen.getByText(/Production/)).toBeInTheDocument();
    expect(screen.getByText(/Genre Authenticity/)).toBeInTheDocument();
  });

  it("shows revision notes when verdict is not RELEASE", () => {
    const reviseEval: QualityEvaluation = {
      ...mockEvaluation,
      verdict: "REVISE",
      scores: { ...mockEvaluation.scores, overall: 5.5 },
      revision_notes: "Cần sửa melody ở chorus.",
    };
    render(
      <EvaluationPanel draft={makeDraft({ evaluation: reviseEval })} />,
    );
    expect(screen.getByText("Hướng dẫn sửa")).toBeInTheDocument();
    expect(screen.getByText("Cần sửa melody ở chorus.")).toBeInTheDocument();
  });

  it("does not show revision notes when verdict is RELEASE", () => {
    render(
      <EvaluationPanel draft={makeDraft({ evaluation: mockEvaluation })} />,
    );
    expect(screen.queryByText("Hướng dẫn sửa")).not.toBeInTheDocument();
  });

  it("shows attempt number when > 1", () => {
    const multiAttempt: QualityEvaluation = {
      ...mockEvaluation,
      attempt: 3,
      max_attempts_reached: true,
    };
    render(
      <EvaluationPanel draft={makeDraft({ evaluation: multiAttempt })} />,
    );
    expect(screen.getByText(/Attempt #3/)).toBeInTheDocument();
    expect(screen.getByText(/max reached/)).toBeInTheDocument();
  });

  it("calls evaluateDraft on button click", async () => {
    const { api } = await import("@/lib/api");
    const mockFn = vi.mocked(api.evaluateDraft);
    mockFn.mockResolvedValueOnce(mockEvaluation);

    const onEvaluationChange = vi.fn();
    render(
      <EvaluationPanel
        draft={makeDraft()}
        onEvaluationChange={onEvaluationChange}
      />,
    );

    fireEvent.click(screen.getByText("Chạy đánh giá A&R"));
    await waitFor(() => {
      expect(mockFn).toHaveBeenCalledWith("test-001");
    });
    await waitFor(() => {
      expect(onEvaluationChange).toHaveBeenCalledWith(mockEvaluation);
    });
  });

  it("shows error message on evaluation failure", async () => {
    const { api } = await import("@/lib/api");
    const mockFn = vi.mocked(api.evaluateDraft);
    mockFn.mockRejectedValueOnce(new Error("Server error"));

    render(<EvaluationPanel draft={makeDraft()} />);

    fireEvent.click(screen.getByText("Chạy đánh giá A&R"));
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });
});

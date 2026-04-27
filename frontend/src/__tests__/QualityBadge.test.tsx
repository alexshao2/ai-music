import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { QualityBadge } from "@/components/QualityBadge";
import type { QualityEvaluation } from "@/lib/api";

function makeEvaluation(
  overrides: Partial<QualityEvaluation> = {},
): QualityEvaluation {
  return {
    scores: {
      melody_catchiness: 7,
      lyric_quality: 7,
      harmonic_sophistication: 6,
      structural_coherence: 7,
      production_direction: 7,
      genre_authenticity: 8,
      overall: 7.0,
    },
    verdict: "REVISE",
    feedback: "",
    revision_notes: "",
    attempt: 1,
    max_attempts_reached: false,
    ...overrides,
  };
}

describe("QualityBadge", () => {
  it("renders RELEASE verdict with correct label", () => {
    render(
      <QualityBadge
        evaluation={makeEvaluation({ verdict: "RELEASE", scores: { ...makeEvaluation().scores, overall: 8.5 } })}
      />,
    );
    expect(screen.getByText("Xuất bản")).toBeInTheDocument();
    expect(screen.getByText("8.5")).toBeInTheDocument();
  });

  it("renders REVISE verdict with correct label", () => {
    render(
      <QualityBadge evaluation={makeEvaluation({ verdict: "REVISE" })} />,
    );
    expect(screen.getByText("Cần sửa")).toBeInTheDocument();
  });

  it("renders REJECT verdict with correct label", () => {
    render(
      <QualityBadge
        evaluation={makeEvaluation({ verdict: "REJECT", scores: { ...makeEvaluation().scores, overall: 3.0 } })}
      />,
    );
    expect(screen.getByText("Từ chối")).toBeInTheDocument();
    expect(screen.getByText("3.0")).toBeInTheDocument();
  });

  it("displays overall score with one decimal", () => {
    render(
      <QualityBadge
        evaluation={makeEvaluation({ scores: { ...makeEvaluation().scores, overall: 7.3 } })}
      />,
    );
    expect(screen.getByText("7.3")).toBeInTheDocument();
  });

  it("applies green styling for RELEASE", () => {
    const { container } = render(
      <QualityBadge evaluation={makeEvaluation({ verdict: "RELEASE" })} />,
    );
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("emerald");
  });

  it("applies amber styling for REVISE", () => {
    const { container } = render(
      <QualityBadge evaluation={makeEvaluation({ verdict: "REVISE" })} />,
    );
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("amber");
  });

  it("applies red styling for REJECT", () => {
    const { container } = render(
      <QualityBadge evaluation={makeEvaluation({ verdict: "REJECT" })} />,
    );
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("red");
  });
});

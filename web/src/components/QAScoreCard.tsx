import React from "react";

interface QAScoreCardProps {
  score?: number;
  blocked?: boolean;
  reasons?: string[];
  fixes?: string[];
  coverageAnalysis?: Record<string, string>;
  keysToProject?: string[];
}

export function QAScoreCard({
  score = 0,
  blocked = false,
  reasons = [],
  fixes = [],
  coverageAnalysis,
  keysToProject,
}: QAScoreCardProps) {
  // Score color logic
  const getScoreColor = (s: number) => {
    if (s >= 85) return "#10b981"; // green
    if (s >= 70) return "#f59e0b"; // yellow
    return "#ef4444"; // red
  };

  const scoreColor = getScoreColor(score);
  const scorePercent = Math.min(100, Math.max(0, score));

  // Coverage status colors
  const getCoverageColor = (status: string) => {
    const s = status.toLowerCase();
    if (s === "complete" || s === "good") return "#10b981";
    if (s === "weak" || s === "partial") return "#f59e0b";
    if (s === "missing" || s === "empty") return "#ef4444";
    return "#6b7280"; // gray
  };

  const apqpDimensions = [
    { key: "keys_to_project", label: "Keys to Project" },
    { key: "quality", label: "Quality Plan" },
    { key: "purchasing", label: "Purchasing" },
    { key: "build", label: "Build Strategy" },
    { key: "schedule", label: "Schedule" },
    { key: "engineering", label: "Engineering" },
    { key: "execution", label: "Execution" },
    { key: "shipping", label: "Shipping" },
  ];

  return (
    <div className="qa-scorecard" style={{ padding: "1.5rem", border: "1px solid #e5e7eb", borderRadius: "8px", backgroundColor: "#f9fafb" }}>
      <h3 style={{ marginTop: 0, marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
        📊 Quality Assessment
        {blocked && (
          <span style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", backgroundColor: "#fee2e2", color: "#991b1b", borderRadius: "4px", fontWeight: "bold" }}>
            ⛔ BLOCKED
          </span>
        )}
      </h3>

      {/* Score Gauge */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.5rem" }}>
          <div style={{ fontSize: "2.5rem", fontWeight: "bold", color: scoreColor }}>
            {Math.round(scorePercent)}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "0.85rem", color: "#6b7280", marginBottom: "0.25rem" }}>
              Quality Score {blocked && "(Needs ≥85 to publish)"}
            </div>
            <div style={{ height: "20px", backgroundColor: "#e5e7eb", borderRadius: "10px", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${scorePercent}%`,
                  backgroundColor: scoreColor,
                  transition: "width 0.3s ease",
                }}
              />
            </div>
          </div>
        </div>
        {blocked && (
          <div style={{ padding: "0.5rem", backgroundColor: "#fee2e2", borderRadius: "4px", fontSize: "0.85rem", color: "#991b1b" }}>
            ⚠️ Publishing is blocked until score reaches 85 or higher. Address the fixes below.
          </div>
        )}
      </div>

      {/* Keys to Project */}
      {keysToProject && keysToProject.length > 0 && (
        <div style={{ marginBottom: "1.5rem", padding: "1rem", backgroundColor: "#fff", borderRadius: "4px", border: "2px solid #3b82f6" }}>
          <h4 style={{ marginTop: 0, marginBottom: "0.75rem", color: "#1e40af" }}>🔑 Keys to the Project</h4>
          <ul style={{ marginLeft: "1.25rem", marginBottom: 0 }}>
            {keysToProject.map((key, i) => (
              <li key={i} style={{ marginBottom: "0.5rem", fontSize: "0.95rem", fontWeight: "500" }}>
                {key}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Coverage Heatmap */}
      {coverageAnalysis && Object.keys(coverageAnalysis).length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h4 style={{ fontSize: "0.95rem", marginBottom: "0.75rem" }}>Coverage by APQP Dimension</h4>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
            {apqpDimensions.map((dim) => {
              const status = coverageAnalysis[dim.key] || "unknown";
              const color = getCoverageColor(status);
              return (
                <div
                  key={dim.key}
                  style={{
                    padding: "0.5rem",
                    backgroundColor: "#fff",
                    border: `2px solid ${color}`,
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                  }}
                >
                  <div style={{ fontWeight: "600", marginBottom: "0.25rem" }}>{dim.label}</div>
                  <div style={{ color, textTransform: "capitalize", fontSize: "0.8rem" }}>
                    {status === "complete" && "✓ Complete"}
                    {status === "weak" && "⚠ Weak"}
                    {status === "missing" && "❌ Missing"}
                    {!["complete", "weak", "missing"].includes(status.toLowerCase()) && status}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reasons */}
      {reasons.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <h4 style={{ fontSize: "0.95rem", marginBottom: "0.5rem" }}>✓ What's Working</h4>
          <ul style={{ marginLeft: "1.25rem", marginBottom: 0, fontSize: "0.9rem" }}>
            {reasons.slice(0, 3).map((reason, i) => (
              <li key={i} style={{ marginBottom: "0.25rem", color: "#065f46" }}>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Fixes */}
      {fixes.length > 0 && (
        <div>
          <h4 style={{ fontSize: "0.95rem", marginBottom: "0.5rem", color: "#dc2626" }}>
            {blocked ? "⛔ Required Fixes" : "💡 Suggested Improvements"}
          </h4>
          <ul style={{ marginLeft: "1.25rem", marginBottom: 0, fontSize: "0.9rem" }}>
            {fixes.map((fix, i) => (
              <li key={i} style={{ marginBottom: "0.5rem", color: blocked ? "#991b1b" : "#6b7280" }}>
                {fix}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty state */}
      {!reasons.length && !fixes.length && !coverageAnalysis && (
        <div style={{ textAlign: "center", color: "#6b7280", fontSize: "0.9rem" }}>
          Generate a plan to see quality assessment
        </div>
      )}
    </div>
  );
}

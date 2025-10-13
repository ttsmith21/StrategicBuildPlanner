import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { MeetingPrepResponseData } from "../types";

interface MeetingPrepViewProps {
  prepData: MeetingPrepResponseData;
  onStartMeeting?: () => void;
}

export function MeetingPrepView({ prepData, onStartMeeting }: MeetingPrepViewProps) {
  const [presentMode, setPresentMode] = useState(false);
  const [activeTab, setActiveTab] = useState<"brief" | "agenda">("brief");

  const handlePrint = () => {
    window.print();
  };

  const handlePresentMode = () => {
    setPresentMode(!presentMode);
    if (!presentMode) {
      // Request fullscreen
      document.documentElement.requestFullscreen?.();
    } else {
      // Exit fullscreen
      document.exitFullscreen?.();
    }
  };

  if (presentMode) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "#fff",
          zIndex: 9999,
          overflow: "auto",
          padding: "3rem",
        }}
      >
        <button
          onClick={handlePresentMode}
          style={{
            position: "fixed",
            top: "1rem",
            right: "1rem",
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            cursor: "pointer",
            backgroundColor: "#333",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
          }}
        >
          Exit Present Mode
        </button>

        <div style={{ maxWidth: "1200px", margin: "0 auto", fontSize: "1.4rem", lineHeight: "1.8" }}>
          {activeTab === "brief" && (
            <div className="project-brief">
              <ReactMarkdown>{prepData.project_brief_markdown}</ReactMarkdown>
            </div>
          )}

          {activeTab === "agenda" && (
            <div className="meeting-agenda">
              <h1>APQP Meeting Agenda</h1>
              <p style={{ fontSize: "1.2rem", color: "#666" }}>
                Total Duration: {prepData.meeting_agenda.total_duration_minutes} minutes
              </p>

              {prepData.meeting_agenda.topics.map((topic, idx) => (
                <div key={idx} style={{ marginBottom: "3rem", pageBreakInside: "avoid" }}>
                  <h2>
                    {idx + 1}. {topic.name} ({topic.suggested_duration_minutes} min)
                  </h2>

                  {topic.discussion_prompts.length > 0 && (
                    <div style={{ marginBottom: "1rem" }}>
                      <h3>Discussion Points:</h3>
                      <ul>
                        {topic.discussion_prompts.map((prompt, i) => (
                          <li key={i}>{prompt}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {topic.known_facts.length > 0 && (
                    <div style={{ marginBottom: "1rem" }}>
                      <h3>Known Facts:</h3>
                      <ul>
                        {topic.known_facts.map((fact, i) => (
                          <li key={i}>{fact}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {topic.open_questions.length > 0 && (
                    <div style={{ marginBottom: "1rem" }}>
                      <h3>Questions to Answer:</h3>
                      <ul>
                        {topic.open_questions.map((q, i) => (
                          <li key={i} style={{ color: "#d97706", fontWeight: "bold" }}>
                            {q}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div
          style={{
            position: "fixed",
            bottom: "1rem",
            left: "50%",
            transform: "translateX(-50%)",
            display: "flex",
            gap: "1rem",
          }}
        >
          <button
            onClick={() => setActiveTab("brief")}
            style={{
              padding: "0.75rem 1.5rem",
              fontSize: "1.1rem",
              cursor: "pointer",
              backgroundColor: activeTab === "brief" ? "#2563eb" : "#666",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
            }}
          >
            Project Brief
          </button>
          <button
            onClick={() => setActiveTab("agenda")}
            style={{
              padding: "0.75rem 1.5rem",
              fontSize: "1.1rem",
              cursor: "pointer",
              backgroundColor: activeTab === "agenda" ? "#2563eb" : "#666",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
            }}
          >
            Meeting Agenda
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="meeting-prep-view" style={{ padding: "1rem" }}>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button
          onClick={handlePresentMode}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            cursor: "pointer",
            backgroundColor: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
          }}
        >
          📽️ Present Mode (Fullscreen)
        </button>
        <button
          onClick={handlePrint}
          style={{
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            cursor: "pointer",
            backgroundColor: "#059669",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
          }}
        >
          🖨️ Print Agenda
        </button>
        {onStartMeeting && (
          <button
            onClick={onStartMeeting}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "1rem",
              cursor: "pointer",
              backgroundColor: "#dc2626",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
            }}
          >
            ▶️ Start Meeting (Record Notes)
          </button>
        )}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button
          onClick={() => setActiveTab("brief")}
          style={{
            padding: "0.5rem 1rem",
            cursor: "pointer",
            backgroundColor: activeTab === "brief" ? "#e5e7eb" : "transparent",
            border: "1px solid #d1d5db",
            borderRadius: "4px 4px 0 0",
            borderBottom: activeTab === "brief" ? "none" : "1px solid #d1d5db",
          }}
        >
          Project Brief
        </button>
        <button
          onClick={() => setActiveTab("agenda")}
          style={{
            padding: "0.5rem 1rem",
            cursor: "pointer",
            backgroundColor: activeTab === "agenda" ? "#e5e7eb" : "transparent",
            border: "1px solid #d1d5db",
            borderRadius: "4px 4px 0 0",
            borderBottom: activeTab === "agenda" ? "none" : "1px solid #d1d5db",
          }}
        >
          Meeting Agenda
        </button>
      </div>

      <div
        style={{
          border: "1px solid #d1d5db",
          borderRadius: "0 4px 4px 4px",
          padding: "1.5rem",
          backgroundColor: "#fff",
          maxHeight: "70vh",
          overflow: "auto",
        }}
      >
        {activeTab === "brief" && (
          <div className="project-brief">
            <ReactMarkdown>{prepData.project_brief_markdown}</ReactMarkdown>

            {prepData.lessons_learned_summary && (
              <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#fef3c7", borderRadius: "4px" }}>
                <h3>📚 Lessons Learned from Customer/Family History</h3>
                <p>{prepData.lessons_learned_summary}</p>
              </div>
            )}

            {prepData.critical_questions.length > 0 && (
              <div style={{ marginTop: "2rem", padding: "1rem", backgroundColor: "#fee2e2", borderRadius: "4px" }}>
                <h3>❓ Critical Questions to Address</h3>
                <ul>
                  {prepData.critical_questions.map((q, i) => (
                    <li key={i} style={{ marginBottom: "0.5rem" }}>
                      {q}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "agenda" && (
          <div className="meeting-agenda">
            <h2>APQP Meeting Agenda</h2>
            <p style={{ color: "#666", marginBottom: "1.5rem" }}>
              Total Duration: {prepData.meeting_agenda.total_duration_minutes} minutes (~
              {Math.round(prepData.meeting_agenda.total_duration_minutes / 60 * 10) / 10} hours)
            </p>

            {prepData.meeting_agenda.topics.map((topic, idx) => (
              <div
                key={idx}
                style={{
                  marginBottom: "2rem",
                  padding: "1rem",
                  border: "1px solid #e5e7eb",
                  borderRadius: "4px",
                  backgroundColor: "#f9fafb",
                }}
              >
                <h3 style={{ marginTop: 0 }}>
                  {idx + 1}. {topic.name}{" "}
                  <span style={{ color: "#6b7280", fontSize: "0.9rem" }}>
                    ({topic.suggested_duration_minutes} min)
                  </span>
                </h3>

                {topic.discussion_prompts.length > 0 && (
                  <div style={{ marginBottom: "1rem" }}>
                    <h4 style={{ fontSize: "0.95rem", color: "#4b5563" }}>Discussion Points:</h4>
                    <ul style={{ marginLeft: "1.5rem" }}>
                      {topic.discussion_prompts.map((prompt, i) => (
                        <li key={i} style={{ marginBottom: "0.25rem" }}>
                          {prompt}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {topic.known_facts.length > 0 && (
                  <div style={{ marginBottom: "1rem" }}>
                    <h4 style={{ fontSize: "0.95rem", color: "#059669" }}>✓ Known Facts:</h4>
                    <ul style={{ marginLeft: "1.5rem" }}>
                      {topic.known_facts.map((fact, i) => (
                        <li key={i} style={{ marginBottom: "0.25rem", color: "#065f46" }}>
                          {fact}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {topic.open_questions.length > 0 && (
                  <div style={{ marginBottom: "1rem" }}>
                    <h4 style={{ fontSize: "0.95rem", color: "#dc2626" }}>❓ Questions to Answer:</h4>
                    <ul style={{ marginLeft: "1.5rem" }}>
                      {topic.open_questions.map((q, i) => (
                        <li key={i} style={{ marginBottom: "0.25rem", color: "#991b1b", fontWeight: "500" }}>
                          {q}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

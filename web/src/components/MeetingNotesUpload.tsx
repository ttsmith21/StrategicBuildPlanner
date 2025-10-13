import React, { useState } from "react";
import { transcribeAudio } from "../api";

interface MeetingNotesUploadProps {
  onGenerate: (notes: string) => void;
  loading?: boolean;
}

export function MeetingNotesUpload({ onGenerate, loading = false }: MeetingNotesUploadProps) {
  const [meetingNotes, setMeetingNotes] = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [transcriptResult, setTranscriptResult] = useState<string | null>(null);

  const handleAudioUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAudioFile(file);

    // Auto-transcribe
    setTranscribing(true);
    try {
      const result = await transcribeAudio(file);
      setTranscriptResult(result.transcript_text);
      setMeetingNotes(result.transcript_text);
    } catch (error) {
      console.error("Transcription failed:", error);
      alert(`Transcription failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setTranscribing(false);
    }
  };

  const handleGenerate = () => {
    if (!meetingNotes.trim()) {
      alert("Please enter meeting notes or upload audio first");
      return;
    }
    onGenerate(meetingNotes);
  };

  const combinedLoading = loading || transcribing;

  return (
    <div className="meeting-notes-upload" style={{ padding: "1rem", border: "1px solid #e5e7eb", borderRadius: "8px", backgroundColor: "#f9fafb" }}>
      <h3 style={{ marginTop: 0 }}>Upload Meeting Notes</h3>
      <p style={{ color: "#6b7280", fontSize: "0.9rem", marginBottom: "1rem" }}>
        Enter meeting notes manually or upload an audio recording for automatic transcription.
      </p>

      {/* Audio Upload Section */}
      <div style={{ marginBottom: "1.5rem" }}>
        <label
          htmlFor="audio-upload"
          style={{
            display: "inline-block",
            padding: "0.5rem 1rem",
            backgroundColor: "#3b82f6",
            color: "#fff",
            borderRadius: "4px",
            cursor: transcribing ? "not-allowed" : "pointer",
            opacity: transcribing ? 0.6 : 1,
          }}
        >
          {transcribing ? "⏳ Transcribing..." : "🎤 Upload Audio Recording"}
        </label>
        <input
          id="audio-upload"
          type="file"
          accept="audio/mp3,audio/mp4,audio/mpeg,audio/mpga,audio/m4a,audio/wav,audio/webm"
          onChange={handleAudioUpload}
          disabled={transcribing}
          style={{ display: "none" }}
        />
        {audioFile && (
          <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#6b7280" }}>
            📎 {audioFile.name} ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
          </div>
        )}
        {transcribing && (
          <div style={{ marginTop: "0.5rem", color: "#3b82f6", fontSize: "0.9rem" }}>
            Transcribing audio... This may take a moment.
          </div>
        )}
        {transcriptResult && !transcribing && (
          <div style={{ marginTop: "0.5rem", color: "#059669", fontSize: "0.9rem" }}>
            ✓ Transcription complete! ({transcriptResult.length} characters)
          </div>
        )}
      </div>

      {/* Manual Notes Section */}
      <div style={{ marginBottom: "1.5rem" }}>
        <label htmlFor="meeting-notes" style={{ display: "block", marginBottom: "0.5rem", fontWeight: "500" }}>
          Meeting Notes (typed or transcribed)
        </label>
        <textarea
          id="meeting-notes"
          value={meetingNotes}
          onChange={(e) => setMeetingNotes(e.target.value)}
          placeholder={`Enter meeting notes here...

Example structure:
- Keys to the Project discussed
- Quality Plan: CTQs identified
- Purchasing: Long-lead items reviewed
- Build Strategy: Fixture approach decided
- Schedule: Key milestones confirmed
- Engineering: Routing steps outlined
- Execution: Material handling plan
- Shipping: Packaging requirements`}
          disabled={transcribing}
          style={{
            width: "100%",
            minHeight: "300px",
            padding: "0.75rem",
            fontSize: "0.95rem",
            fontFamily: "monospace",
            border: "1px solid #d1d5db",
            borderRadius: "4px",
            resize: "vertical",
            backgroundColor: "#fff",
          }}
        />
        <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#6b7280" }}>
          {meetingNotes.length} characters • {meetingNotes.split(/\s+/).filter(Boolean).length} words
        </div>
      </div>

      {/* Generate Button */}
      <div>
        <button
          onClick={handleGenerate}
          disabled={combinedLoading || !meetingNotes.trim()}
          style={{
            padding: "0.75rem 1.5rem",
            fontSize: "1rem",
            fontWeight: "600",
            backgroundColor: combinedLoading || !meetingNotes.trim() ? "#d1d5db" : "#10b981",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: combinedLoading || !meetingNotes.trim() ? "not-allowed" : "pointer",
          }}
        >
          {combinedLoading ? "⏳ Generating..." : "✨ Generate Strategic Build Plan"}
        </button>
        <p style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "#6b7280" }}>
          This will extract "Keys to the Project" (1-5 bullets) and generate a complete Strategic Build Plan
          across all 8 APQP dimensions.
        </p>
      </div>
    </div>
  );
}

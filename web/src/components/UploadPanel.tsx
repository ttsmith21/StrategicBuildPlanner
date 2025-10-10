import { ChangeEvent, FormEvent, useRef, useState } from "react";
import { PlannerMeta } from "../types";

interface UploadPanelProps {
  meta: PlannerMeta;
  onMetaChange: (update: Partial<PlannerMeta>) => void;
  onUpload: (files: FileList) => Promise<void>;
  uploading: boolean;
  sessionId?: string | null;
  uploadedFiles: string[];
}

export function UploadPanel({
  meta,
  onMetaChange,
  onUpload,
  uploading,
  sessionId,
  uploadedFiles,
}: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleInputChange = (
    event: ChangeEvent<HTMLInputElement>,
    field: keyof PlannerMeta
  ) => {
    onMetaChange({ [field]: event.target.value });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const files = fileInputRef.current?.files;

    if (!files || files.length === 0) {
      setLocalError("Please select one or more files to ingest.");
      return;
    }

    setLocalError(null);
    await onUpload(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="panel">
      <h2>Upload & Session</h2>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <label htmlFor="projectName">Project / Part Family</label>
          <input
            id="projectName"
            name="projectName"
            type="text"
            placeholder="ACME Bracket Demo"
            value={meta.projectName}
            onChange={(event) => handleInputChange(event, "projectName")}
            required
          />
        </fieldset>

        <fieldset>
          <label htmlFor="customer">Customer</label>
          <input
            id="customer"
            name="customer"
            type="text"
            placeholder="Northern Manufacturing"
            value={meta.customer}
            onChange={(event) => handleInputChange(event, "customer")}
          />
        </fieldset>

        <fieldset>
          <label htmlFor="family">Family</label>
          <input
            id="family"
            name="family"
            type="text"
            placeholder="Bracket Assemblies"
            value={meta.family}
            onChange={(event) => handleInputChange(event, "family")}
          />
        </fieldset>

        <fieldset>
          <label htmlFor="ingest-files">Source Documents</label>
          <input
            id="ingest-files"
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.md,.json"
          />
        </fieldset>

        {localError && <div className="error-banner">{localError}</div>}

        <button type="submit" disabled={uploading}>
          {uploading ? "Uploading…" : "Upload & Create Session"}
        </button>
      </form>

      <section>
        <div className="status-line">
          Session: {sessionId ? sessionId : "—"}
        </div>
        <div className="listing" style={{ marginTop: "0.75rem" }}>
          {uploadedFiles.length === 0 ? (
            <span className="small">No files ingested yet.</span>
          ) : (
            uploadedFiles.map((file) => (
              <div key={file} className="badge">
                📄 {file}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Toast } from "./ToastContainer";
import {
  ConfluencePageSummary,
  PlannerMeta,
} from "../types";

// Defaults aligned with server/lib/context_pack.py
const DEFAULT_AUTHORITY: Record<string, string> = {
  drawing: "mandatory",
  po: "mandatory",
  quote: "conditional",
  itp: "mandatory",
  sow_spec: "mandatory",
  customer_spec: "mandatory",
  supplier_qm: "conditional",
  generic_spec: "reference",
  meeting_notes: "mandatory",
  email: "internal",
  lessons_learned: "internal",
  other: "reference",
};

const DEFAULT_PRECEDENCE_RANK: Record<string, number> = {
  drawing: 1,
  po: 1,
  quote: 2,
  itp: 2,
  sow_spec: 2,
  customer_spec: 3,
  supplier_qm: 4,
  generic_spec: 5,
  meeting_notes: 6,
  email: 20,
  lessons_learned: 6,
  other: 10,
};

function inferDocTypeFromName(name: string): string | undefined {
  const n = name.toLowerCase();
  if (/(drawing|dwg|dxf|print)/.test(n)) return "drawing";
  if (/(purchase[ _-]?order|^po[ _-]|\bpo\b)/.test(n)) return "po";
  if (/(quote|proposal|bid)/.test(n)) return "quote";
  if (/(\bitp\b|inspection.*test.*plan)/.test(n)) return "itp";
  if (/(sow|statement of work|project spec|project standard)/.test(n)) return "sow_spec";
  if (/(customer).*spec/.test(n)) return "customer_spec";
  if (/(supplier).*qm/.test(n)) return "supplier_qm";
  if (/(meeting|minutes|notes)/.test(n)) return "meeting_notes";
  if (/spec/.test(n)) return "generic_spec";
  if (/(email|mail)/.test(n)) return "email";
  if (/(lessons|retro)/.test(n)) return "lessons_learned";
  return undefined;
}

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(handle);
  }, [value, delay]);
  return debounced;
}

interface UploadPanelProps {
  meta: PlannerMeta;
  onMetaChange: (update: Partial<PlannerMeta>) => void;
  onUpload: (files: FileList) => Promise<void>;
  uploading: boolean;
  sessionId?: string | null;
  vectorStoreId?: string | null;
  uploadedFiles: string[];
  selectedCustomer?: ConfluencePageSummary | null;
  selectedFamily?: ConfluencePageSummary | null;
  recentCustomers: ConfluencePageSummary[];
  recentFamilies: ConfluencePageSummary[];
  onCustomerSelected: (page: ConfluencePageSummary | null) => void;
  onFamilySelected: (page: ConfluencePageSummary | null) => void;
  onFamilyUrlPaste: (url: string) => Promise<void> | void;
  pushToast: (type: Toast["type"], message: string) => void;
  onGenerateMeetingPrep?: () => void;
}

export function UploadPanel({
  meta,
  onMetaChange,
  onUpload,
  uploading,
  sessionId,
  vectorStoreId,
  uploadedFiles,
  selectedCustomer,
  selectedFamily,
  recentCustomers,
  recentFamilies,
  onCustomerSelected,
  onFamilySelected,
  onFamilyUrlPaste,
  pushToast,
  onGenerateMeetingPrep,
}: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [pendingMeta, setPendingMeta] = useState<Record<string, { doc_type?: string; authority?: string; precedence_rank?: number | string }>>({});
  const [localError, setLocalError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customerFocused, setCustomerFocused] = useState(false);
  const [familyFocused, setFamilyFocused] = useState(false);
  const blurTimeoutRef = useRef<number | null>(null);
  const [customerQuery, setCustomerQuery] = useState(meta.customer);
  const [familyQuery, setFamilyQuery] = useState(meta.family);

  const debouncedCustomer = useDebouncedValue(customerQuery);
  const debouncedFamily = useDebouncedValue(familyQuery);

  useEffect(() => {
    setCustomerQuery(meta.customer);
  }, [meta.customer]);

  useEffect(() => {
    setFamilyQuery(meta.family);
  }, [meta.family]);

  const handleInputChange = (
    event: ChangeEvent<HTMLInputElement>,
    field: keyof PlannerMeta
  ) => {
    onMetaChange({ [field]: event.target.value });
    if (field === "customer") {
      setCustomerQuery(event.target.value);
      if (selectedCustomer && selectedCustomer.title !== event.target.value) {
        onCustomerSelected(null);
      }
    }
    if (field === "family") {
      setFamilyQuery(event.target.value);
      if (selectedFamily && selectedFamily.title !== event.target.value) {
        onFamilySelected(null);
      }
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const files = fileInputRef.current?.files;

    if (!files || files.length === 0) {
      setLocalError("Please select one or more files to ingest.");
      return;
    }

    setLocalError(null);
    // merge pendingMeta into meta.filesMeta before upload
    if (Object.keys(pendingMeta).length > 0) {
      onMetaChange({ filesMeta: { ...(meta.filesMeta || {}), ...pendingMeta } });
    }
    await onUpload(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    setSelectedFiles([]);
    setPendingMeta({});
  };

  const { data: customerResults } = useQuery<ConfluencePageSummary[]>({
    queryKey: ["confluence-customers", debouncedCustomer],
    queryFn: async () => {
      if (!debouncedCustomer) {
        return recentCustomers;
      }
      const { data } = await api.get<ConfluencePageSummary[]>("/confluence/customers", {
        params: { q: debouncedCustomer },
      });
      return data.length > 0 ? data : recentCustomers;
    },
    enabled: debouncedCustomer.trim().length >= 1,
    initialData: recentCustomers,
  });

  const { data: familyResults } = useQuery<ConfluencePageSummary[]>({
    queryKey: ["confluence-families", debouncedFamily, selectedCustomer?.id || null],
    queryFn: async () => {
      if (!debouncedFamily) {
        return recentFamilies;
      }
      const { data } = await api.get<ConfluencePageSummary[]>("/confluence/families", {
        params: { q: debouncedFamily, parent_id: selectedCustomer?.id },
      });
      return data.length > 0 ? data : recentFamilies;
    },
    enabled: debouncedFamily.trim().length >= 1,
    initialData: recentFamilies,
  });

  const handleChooseCustomer = (page: ConfluencePageSummary) => {
    onCustomerSelected(page);
    onMetaChange({ customer: page.title, customerPage: page });
    setCustomerFocused(false);
  };

  const handleChooseFamily = (page: ConfluencePageSummary) => {
    onFamilySelected(page);
    onMetaChange({ family: page.title, familyPage: page });
    setFamilyFocused(false);
  };

  const handlePasteFamilyUrl = async () => {
    const url = window.prompt("Paste Confluence family page URL");
    if (!url) {
      return;
    }
    await onFamilyUrlPaste(url);
  };

  const customerOptions = customerResults ?? [];
  const familyOptions = familyResults ?? [];

  return (
    <div className="panel">
  <h2>Upload & Project</h2>

      <form onSubmit={handleSubmit}>
        <fieldset>
          <label htmlFor="projectName">Project Title</label>
          <input
            id="projectName"
            name="projectName"
            type="text"
            placeholder="e.g., ACME Bracket APQP Plan"
            value={meta.projectName}
            onChange={(event) => handleInputChange(event, "projectName")}
            // Only required when starting a new project (no existing vector store)
            required={!vectorStoreId}
            title="This names the APQP project; it's used for the vector store and as the default Confluence page title on publish."
          />
          <div className="small" style={{ marginTop: "0.25rem" }}>
            {vectorStoreId
              ? "Optional while resuming: this is your plan title (used when publishing)."
              : "Required for a new project: this will be the plan title and default Confluence page title."}
          </div>
        </fieldset>

        <fieldset>
          <label htmlFor="customer">Customer</label>
          <input
            id="customer"
            name="customer"
            type="text"
            placeholder="Northern Manufacturing"
            value={meta.customer}
            onFocus={() => setCustomerFocused(true)}
            onBlur={() => {
              if (blurTimeoutRef.current) window.clearTimeout(blurTimeoutRef.current);
              blurTimeoutRef.current = window.setTimeout(() => setCustomerFocused(false), 150);
            }}
            onChange={(event) => handleInputChange(event, "customer")}
          />
          {customerFocused && customerOptions.length > 0 && (
            <div className="autocomplete-menu">
              {customerOptions.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  className="autocomplete-item"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleChooseCustomer(option)}
                >
                  <span>{option.title}</span>
                </button>
              ))}
            </div>
          )}
          {customerFocused && customerOptions.length === 0 && debouncedCustomer.trim().length > 1 && (
            <div className="autocomplete-empty">Can't find it? Try a different keyword.</div>
          )}
          {selectedCustomer && (
            <div className="badge" style={{ marginTop: "0.35rem" }}>
              Customer page: {selectedCustomer.title}
            </div>
          )}
        </fieldset>

        <fieldset>
          <label htmlFor="family">Family</label>
          <input
            id="family"
            name="family"
            type="text"
            placeholder="Bracket Assemblies"
            value={meta.family}
            onFocus={() => setFamilyFocused(true)}
            onBlur={() => {
              if (blurTimeoutRef.current) window.clearTimeout(blurTimeoutRef.current);
              blurTimeoutRef.current = window.setTimeout(() => setFamilyFocused(false), 150);
            }}
            onChange={(event) => handleInputChange(event, "family")}
          />
          {familyFocused && familyOptions.length > 0 && (
            <div className="autocomplete-menu">
              {familyOptions.map((option) => (
                <button
                  type="button"
                  key={option.id}
                  className="autocomplete-item"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => handleChooseFamily(option)}
                >
                  <span>{option.title}</span>
                </button>
              ))}
            </div>
          )}
          {familyFocused && familyOptions.length === 0 && debouncedFamily.trim().length > 1 && (
            <div className="autocomplete-empty">
              Can't find it? <button type="button" className="link-button" onClick={handlePasteFamilyUrl}>Paste the Confluence page URL</button>
            </div>
          )}
          {!familyFocused && (
            <button
              type="button"
              className="link-button"
              style={{ marginTop: "0.35rem" }}
              onClick={handlePasteFamilyUrl}
            >
              Paste Confluence URL
            </button>
          )}
          {selectedFamily && (
            <div className="badge" style={{ marginTop: "0.35rem" }}>
              Selected parent: {selectedFamily.title}
              {selectedFamily.url && (
                <button
                  type="button"
                  className="link-button"
                  style={{ marginLeft: "0.5rem" }}
                  onClick={() => {
                    if (!selectedFamily.url) {
                      pushToast("error", "No URL available to open");
                      return;
                    }
                    try {
                      window.open(selectedFamily.url, "_blank", "noopener");
                    } catch (error) {
                      pushToast("error", "Failed to open URL. Popup may be blocked.");
                    }
                  }}
                >
                  Open ↗
                </button>
              )}
            </div>
          )}
        </fieldset>

        <fieldset>
          <label htmlFor="ingest-files">Source Documents</label>
          <input
            id="ingest-files"
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.md,.json"
            onChange={() => {
              const files = fileInputRef.current?.files;
              const names = files ? Array.from(files).map((f) => f.name) : [];
              setSelectedFiles(names);
              // Initialize pendingMeta keys so selectors show per-file state
              const init: typeof pendingMeta = {};
              names.forEach((n) => {
                const key = n.toLowerCase();
                const current = pendingMeta[key] || {};
                // Pre-infer doc_type from filename on first touch to reduce work
                const inferred = current.doc_type || inferDocTypeFromName(n);
                init[key] = { ...current, ...(inferred ? { doc_type: inferred } : {}) };
              });
              if (Object.keys(init).length) {
                setPendingMeta((prev) => ({ ...init, ...prev }));
              }
            }}
          />
          <div className="small" style={{ marginTop: "0.35rem", display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <label style={{ display: "inline-flex", gap: "0.35rem", alignItems: "center" }}>
              <input type="checkbox" checked={showAdvanced} onChange={(e) => setShowAdvanced(e.target.checked)} />
              Advanced overrides
            </label>
            {selectedFiles.length > 1 && (
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  const first = selectedFiles[0]?.toLowerCase();
                  const firstDoc = first ? pendingMeta[first]?.doc_type : undefined;
                  if (!firstDoc) return;
                  setPendingMeta((prev) => {
                    const next = { ...prev } as typeof pendingMeta;
                    selectedFiles.forEach((name) => {
                      const key = name.toLowerCase();
                      next[key] = { ...(next[key] || {}), doc_type: firstDoc };
                      if (!showAdvanced) {
                        // when not advanced, let server pick authority/precedence; clear any stale overrides
                        delete next[key].authority;
                        delete (next[key] as any).precedence_rank;
                      }
                    });
                    return next;
                  });
                }}
              >
                Apply first doc type to all
              </button>
            )}
          </div>
        </fieldset>

        {selectedFiles.length > 0 && (
          <fieldset>
            <label>Per-file tags</label>
            <div className="listing" style={{ padding: "0.5rem" }}>
              {selectedFiles.map((name) => {
                const key = name.toLowerCase();
                const metaRow = pendingMeta[key] || {};
                const autoAuth = DEFAULT_AUTHORITY[metaRow.doc_type || ""] || undefined;
                const autoPrec = DEFAULT_PRECEDENCE_RANK[metaRow.doc_type || ""];
                return (
                  <div key={name} style={{ display: "grid", gridTemplateColumns: showAdvanced ? "2fr 1fr 1fr 1fr" : "2fr 1fr auto", gap: "0.5rem", alignItems: "center", marginBottom: "0.35rem" }}>
                    <div className="small" title={name} style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>📄 {name}</div>
                    <select
                      value={metaRow.doc_type || ""}
                      onChange={(e) => setPendingMeta((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), doc_type: e.target.value || undefined } }))}
                    >
                      <option value="">doc type…</option>
                      <option value="drawing">drawing</option>
                      <option value="po">po</option>
                      <option value="itp">itp</option>
                      <option value="sow_spec">sow_spec</option>
                      <option value="customer_spec">customer_spec</option>
                      <option value="generic_spec">generic_spec</option>
                      <option value="meeting_notes">meeting_notes</option>
                      <option value="lessons_learned">lessons_learned</option>
                      <option value="other">other</option>
                    </select>
                    {showAdvanced ? (
                      <>
                        <select
                          value={(metaRow.authority as string) || (autoAuth || "")}
                          onChange={(e) => setPendingMeta((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), authority: (e.target.value || undefined) as any } }))}
                        >
                          <option value="">auto</option>
                          <option value="mandatory">mandatory</option>
                          <option value="conditional">conditional</option>
                          <option value="reference">reference</option>
                          <option value="internal">internal</option>
                        </select>
                        <select
                          value={(metaRow.precedence_rank as string | number) || (autoPrec ?? "")}
                          onChange={(e) => setPendingMeta((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), precedence_rank: (e.target.value || undefined) as any } }))}
                        >
                          <option value="">auto</option>
                          <option value={1}>1</option>
                          <option value={2}>2</option>
                          <option value={3}>3</option>
                          <option value={4}>4</option>
                          <option value={5}>5</option>
                          <option value={6}>6</option>
                          <option value={10}>10</option>
                          <option value={20}>20</option>
                        </select>
                      </>
                    ) : (
                      <div className="small" style={{ opacity: 0.8 }}>
                        {metaRow.doc_type ? (
                          <>
                            auto: {autoAuth || "reference"}
                            {typeof autoPrec === "number" ? ` · rank ${autoPrec}` : ""}
                          </>
                        ) : (
                          "Select a doc type"
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="small" style={{ marginTop: "0.25rem" }}>These tags are optional hints to the planner and precedence policy.</div>
          </fieldset>
        )}

        {localError && <div className="error-banner">{localError}</div>}

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading…" : sessionId ? "Add files to project" : "Upload files"}
          </button>
          {sessionId && (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                // Clear only local UI state; session persists server-side
                if (!window.confirm("Start a new project? Current project will be preserved and can be resumed.")) return;
                onMetaChange({ projectName: "", customer: "", family: "" });
                if (fileInputRef.current) fileInputRef.current.value = "";
                setSelectedFiles([]);
                setPendingMeta({});
                // Let the app clear session id (app owns it); simplest is to reload for now
                window.location.reload();
              }}
            >
              New Project
            </button>
          )}
        </div>
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

        {uploadedFiles.length > 0 && sessionId && onGenerateMeetingPrep && (
          <div style={{ marginTop: "1rem" }}>
            <button
              type="button"
              onClick={onGenerateMeetingPrep}
              style={{
                padding: "0.75rem 1.5rem",
                fontSize: "1rem",
                fontWeight: "600",
                backgroundColor: "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                width: "100%",
              }}
            >
              📋 Generate Meeting Prep (Brief + Agenda)
            </button>
            <div className="small" style={{ marginTop: "0.5rem", textAlign: "center" }}>
              Prepare materials to present at the start of your APQP meeting
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

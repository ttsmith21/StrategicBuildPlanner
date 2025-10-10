import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import {
  ConfluencePageSummary,
  PlannerMeta,
} from "../types";

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
  uploadedFiles: string[];
  selectedCustomer?: ConfluencePageSummary | null;
  selectedFamily?: ConfluencePageSummary | null;
  recentCustomers: ConfluencePageSummary[];
  recentFamilies: ConfluencePageSummary[];
  onCustomerSelected: (page: ConfluencePageSummary | null) => void;
  onFamilySelected: (page: ConfluencePageSummary | null) => void;
  onFamilyUrlPaste: (url: string) => Promise<void> | void;
}

export function UploadPanel({
  meta,
  onMetaChange,
  onUpload,
  uploading,
  sessionId,
  uploadedFiles,
  selectedCustomer,
  selectedFamily,
  recentCustomers,
  recentFamilies,
  onCustomerSelected,
  onFamilySelected,
  onFamilyUrlPaste,
}: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [customerFocused, setCustomerFocused] = useState(false);
  const [familyFocused, setFamilyFocused] = useState(false);
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
    await onUpload(files);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
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
    enabled: debouncedCustomer.trim().length > 1,
    initialData: recentCustomers,
  });

  const { data: familyResults } = useQuery<ConfluencePageSummary[]>({
    queryKey: ["confluence-families", debouncedFamily],
    queryFn: async () => {
      if (!debouncedFamily) {
        return recentFamilies;
      }
      const { data } = await api.get<ConfluencePageSummary[]>("/confluence/families", {
        params: { q: debouncedFamily },
      });
      return data.length > 0 ? data : recentFamilies;
    },
    enabled: debouncedFamily.trim().length > 1,
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
            onFocus={() => setCustomerFocused(true)}
            onBlur={() => setTimeout(() => setCustomerFocused(false), 150)}
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
            onBlur={() => setTimeout(() => setFamilyFocused(false), 150)}
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
                  onClick={() => window.open(selectedFamily.url, "_blank", "noopener")}
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

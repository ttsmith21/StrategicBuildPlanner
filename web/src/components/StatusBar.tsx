import { AuthStatusResponse, VersionInfo } from "../types";

interface StatusBarProps {
  healthStatus: "unknown" | "ok" | "error";
  confluenceStatus?: AuthStatusResponse;
  asanaStatus?: AuthStatusResponse;
  onRefresh?: () => void;
  onToggleAbout: () => void;
  aboutOpen: boolean;
  versionInfo?: VersionInfo;
}

function badgeClass(status: "unknown" | "ok" | "error") {
  if (status === "ok") {
    return "status-badge ok";
  }
  if (status === "error") {
    return "status-badge error";
  }
  return "status-badge unknown";
}

function authStatusLabel(status?: AuthStatusResponse) {
  if (!status) {
    return { text: "Unknown", tone: "unknown" as const };
  }
  return status.ok
    ? { text: "OK", tone: "ok" as const }
    : { text: status.reason ? `Error: ${status.reason}` : "Error", tone: "error" as const };
}

export function StatusBar({
  healthStatus,
  confluenceStatus,
  asanaStatus,
  onRefresh,
  onToggleAbout,
  aboutOpen,
  versionInfo,
}: StatusBarProps) {
  const confluence = authStatusLabel(confluenceStatus);
  const asana = authStatusLabel(asanaStatus);

  return (
    <header className="status-bar">
      <div className="status-items">
        <span className={badgeClass(healthStatus)}>API: {healthStatus.toUpperCase()}</span>
        <span className={`status-badge ${confluence.tone}`}>
          Confluence: {confluence.text}
        </span>
        <span className={`status-badge ${asana.tone}`}>
          Asana: {asana.text}
        </span>
        {onRefresh && (
          <button type="button" className="secondary" onClick={onRefresh}>
            Refresh
          </button>
        )}
      </div>
      <div className="about-area">
        <button type="button" className="secondary" onClick={onToggleAbout}>
          About
        </button>
        {aboutOpen && versionInfo && (
          <div className="about-popover">
            <div><strong>Version:</strong> {versionInfo.version}</div>
            <div><strong>Build:</strong> {versionInfo.build_sha}</div>
            {versionInfo.build_time && <div><strong>Build Time:</strong> {versionInfo.build_time}</div>}
            {versionInfo.model && <div><strong>Model:</strong> {versionInfo.model}</div>}
            {versionInfo.prompt_version && <div><strong>Prompt:</strong> {versionInfo.prompt_version}</div>}
            {versionInfo.schema_version && <div><strong>Schema:</strong> {versionInfo.schema_version}</div>}
          </div>
        )}
      </div>
    </header>
  );
}

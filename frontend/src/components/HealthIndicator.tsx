import { useState } from "react";
import { Activity, CheckCircle, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import type { HealthReport } from "../api/types";

interface Props {
  health: HealthReport | null;
  loading: boolean;
  onRefresh: () => void;
}

export default function HealthIndicator({ health, loading, onRefresh }: Props) {
  const [showDetails, setShowDetails] = useState(false);

  if (!health) {
    return (
      <button
        className="health-status-btn"
        onClick={onRefresh}
        title="Backend unreachable — click to retry"
      >
        <span className={`status-indicator-dot ${loading ? "" : "bad"}`} />
        <span>{loading ? "Connecting…" : "API Offline"}</span>
        <RefreshCw size={12} className={loading ? "spin-slow" : ""} />
      </button>
    );
  }

  const local = health.llm.local;
  const gemini = health.llm.gemini;
  const embeddings = health.embeddings;
  const ok = health.status === "ok" && embeddings.available;
  const dotClass = ok ? "ok" : "warn";

  return (
    <div style={{ position: "relative" }}>
      <button
        className="health-status-btn"
        onClick={() => setShowDetails(!showDetails)}
        title="Click to view detailed system health"
      >
        <span className={`status-indicator-dot ${dotClass}`} />
        <span>{ok ? "System Online" : "Degraded"}</span>
        <Activity size={13} style={{ color: "#94a3b8" }} />
      </button>

      {showDetails && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            zIndex: 100,
            background: "#0f172a",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: "14px",
            boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
            padding: "1rem",
            width: "270px",
            color: "#e2e8f0",
            fontSize: "0.82rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", borderBottom: "1px solid rgba(255,255,255,0.08)", paddingBottom: "0.5rem" }}>
            <strong style={{ color: "#ffffff", fontSize: "0.88rem" }}>System Services</strong>
            <button
              className="ghost sm"
              style={{ color: "#94a3b8", padding: "0.2rem 0.4rem" }}
              onClick={(e) => {
                e.stopPropagation();
                onRefresh();
              }}
              title="Refresh status"
            >
              <RefreshCw size={12} className={loading ? "spin-slow" : ""} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Database:</span>
              <span style={{ color: health.database.ok ? "#34d399" : "#f87171", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                {health.database.ok ? <CheckCircle size={12} /> : <XCircle size={12} />}
                {health.database.ok ? "Connected" : "Down"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Local Ollama:</span>
              <span style={{ color: local.available && local.default_model_available ? "#34d399" : local.available ? "#fbbf24" : "#f87171", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                {local.available && local.default_model_available ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                {local.available ? (local.default_model_available ? "Ready" : "Model Missing") : "Offline"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Embeddings:</span>
              <span style={{ color: embeddings.available ? "#34d399" : "#f87171", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                {embeddings.available ? <CheckCircle size={12} /> : <XCircle size={12} />}
                {embeddings.available ? "Active" : "Unavailable"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span>Google Gemini:</span>
              <span style={{ color: gemini.available ? "#34d399" : "#94a3b8", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                {gemini.available ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
                {gemini.available ? "Ready" : "No API Key"}
              </span>
            </div>
          </div>

          <button
            className="secondary sm"
            style={{ width: "100%", marginTop: "0.75rem", fontSize: "0.78rem" }}
            onClick={() => setShowDetails(false)}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  History as HistoryIcon,
  Award,
  TrendingUp,
  RefreshCw,
  Trash2,
  ArrowRight,
  Filter,
  Calendar,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { AttemptSummary } from "../api/types";
import Spinner from "../components/Spinner";
import { formatDateTime, scorePercent } from "../utils/format";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export default function HistoryPage() {
  const [attempts, setAttempts] = useState<AttemptSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modeFilter, setModeFilter] = useState<string>("all");
  const [deleteTarget, setDeleteTarget] = useState<AttemptSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setAttempts(await api.listAttempts());
      setError(null);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(() => {
    if (attempts.length === 0) return { total: 0, avgPercent: 0, bestPercent: 0 };
    let sumPercent = 0;
    let maxPercent = 0;
    let validCount = 0;

    for (const a of attempts) {
      if (a.max_score && a.max_score > 0) {
        const pct = Math.round(((a.total_score ?? 0) / a.max_score) * 100);
        sumPercent += pct;
        if (pct > maxPercent) maxPercent = pct;
        validCount++;
      }
    }

    const avg = validCount > 0 ? Math.round(sumPercent / validCount) : 0;
    return {
      total: attempts.length,
      avgPercent: avg,
      bestPercent: maxPercent,
    };
  }, [attempts]);

  const filteredAttempts = useMemo(() => {
    return attempts.filter((a) => {
      if (modeFilter !== "all" && a.mode !== modeFilter) return false;
      return true;
    });
  }, [attempts, modeFilter]);

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteAttempt(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div className="page-header-text">
          <h1>Attempt History</h1>
          <p>Review all your past quiz submissions, AI evaluation scores, and track your study progress.</p>
        </div>
        <button
          type="button"
          className="secondary"
          onClick={load}
          disabled={loading}
        >
          <RefreshCw size={14} className={loading ? "spin-slow" : ""} /> Refresh
        </button>
      </div>

      {error && (
        <div className="alert error">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid-three" style={{ marginBottom: "1.75rem" }}>
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#e0e7ff", color: "#4f46e5" }}>
            <HistoryIcon size={24} />
          </div>
          <div>
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total Submissions</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#dcfce7", color: "#16a34a" }}>
            <TrendingUp size={24} />
          </div>
          <div>
            <div className="stat-value">{stats.avgPercent}%</div>
            <div className="stat-label">Average Accuracy</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#fef3c7", color: "#d97706" }}>
            <Award size={24} />
          </div>
          <div>
            <div className="stat-value">{stats.bestPercent}%</div>
            <div className="stat-label">Personal Best Score</div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      {attempts.length > 0 && (
        <div className="card" style={{ padding: "0.85rem 1.25rem", marginBottom: "1.5rem" }}>
          <div className="row-between">
            <div className="row" style={{ gap: "0.5rem" }}>
              <Filter size={15} style={{ color: "#64748b" }} />
              <span className="small muted">Filter by Model:</span>
              <select
                value={modeFilter}
                onChange={(e) => setModeFilter(e.target.value)}
                style={{ width: "auto", padding: "0.35rem 0.75rem", fontSize: "0.84rem" }}
              >
                <option value="all">All Models</option>
                <option value="local">Local (Ollama)</option>
                <option value="gemini">Google Gemini</option>
              </select>
            </div>
            <span className="small muted">
              Showing <strong>{filteredAttempts.length}</strong> of {attempts.length} attempts
            </span>
          </div>
        </div>
      )}

      {/* Attempts Table */}
      <section className="card">
        {loading && attempts.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
            <Spinner dark />
            <p className="muted small" style={{ marginTop: "0.5rem" }}>Loading history…</p>
          </div>
        ) : filteredAttempts.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3.5rem 1rem" }}>
            <HelpCircle size={44} style={{ color: "#cbd5e1", margin: "0 auto 0.75rem" }} />
            <h3>No submissions found</h3>
            <p className="muted small" style={{ maxWidth: "400px", margin: "0 auto 1.5rem" }}>
              {attempts.length === 0
                ? "You haven't taken any quizzes yet. Generate and take a quiz to see your performance here."
                : "No quiz attempts match the selected filter."}
            </p>
            {attempts.length === 0 && (
              <Link to="/quizzes" className="btn primary">
                Browse Quizzes <ArrowRight size={15} />
              </Link>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Attempt</th>
                  <th>Quiz</th>
                  <th>Score</th>
                  <th>Accuracy</th>
                  <th>Evaluation Mode</th>
                  <th>Submitted At</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAttempts.map((attempt) => {
                  const total = attempt.total_score ?? 0;
                  const max = attempt.max_score ?? 0;
                  const pct = max > 0 ? scorePercent(total, max) : 0;

                  return (
                    <tr key={attempt.id}>
                      <td>
                        <strong>#{attempt.id}</strong>
                      </td>
                      <td>
                        <Link to={`/quizzes/${attempt.quiz_id}`} style={{ fontWeight: 600 }}>
                          Quiz #{attempt.quiz_id}
                        </Link>
                      </td>
                      <td>
                        <span style={{ fontWeight: 700 }}>
                          {attempt.total_score != null ? `${total} / ${max}` : "—"}
                        </span>
                        <span className="small muted" style={{ marginLeft: "0.25rem" }}>pts</span>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span
                            className="badge"
                            style={{
                              background:
                                pct >= 80 ? "#ecfdf5" : pct >= 50 ? "#fffbeb" : "#fef2f2",
                              color:
                                pct >= 80 ? "#065f46" : pct >= 50 ? "#92400e" : "#991b1b",
                            }}
                          >
                            {pct}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="chip" style={{ textTransform: "capitalize" }}>
                          {attempt.mode}
                        </span>
                      </td>
                      <td className="small muted">
                        <div className="row" style={{ gap: "0.35rem" }}>
                          <Calendar size={13} style={{ color: "#94a3b8" }} />
                          <span>{formatDateTime(attempt.created_at)}</span>
                        </div>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <div className="row" style={{ justifyContent: "flex-end", gap: "0.5rem" }}>
                          <Link to={`/attempts/${attempt.id}`} className="btn primary sm">
                            View Feedback
                          </Link>
                          <button
                            type="button"
                            className="danger sm"
                            onClick={() => setDeleteTarget(attempt)}
                            title="Delete this attempt"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: "#fee2e2",
                  color: "#dc2626",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0 }}>Delete Attempt #{deleteTarget.id}?</h3>
                <span className="muted small">Remove this score and answer feedback.</span>
              </div>
            </div>

            <p className="small muted" style={{ marginBottom: "1.5rem" }}>
              Are you sure you want to delete this submission record? This action cannot be undone.
            </p>

            <div className="row-between">
              <button
                type="button"
                className="secondary"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="danger"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? <>Deleting… <Spinner /></> : "Yes, Delete Attempt"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

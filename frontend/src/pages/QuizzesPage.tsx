import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  HelpCircle,
  Play,
  Trash2,
  Filter,
  FileText,
  Sparkles,
  Layers,
  ArrowRight,
  PlusCircle,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { DocumentRead, QuizRead } from "../api/types";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { formatDateTime } from "../utils/format";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export default function QuizzesPage() {
  const [quizzes, setQuizzes] = useState<QuizRead[]>([]);
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docFilter, setDocFilter] = useState<number | "all">("all");
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");
  const [deleteTarget, setDeleteTarget] = useState<QuizRead | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [fetchedQuizzes, fetchedDocs] = await Promise.all([
        api.listQuizzes(),
        api.listDocuments(),
      ]);
      setQuizzes(fetchedQuizzes);
      setDocuments(fetchedDocs);
      setError(null);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Polling if any quiz is generating
  const hasGenerating = useMemo(
    () => quizzes.some((q) => q.status === "generating"),
    [quizzes],
  );

  useEffect(() => {
    if (!hasGenerating) return;
    const timer = setInterval(() => void loadData(), 3000);
    return () => clearInterval(timer);
  }, [hasGenerating, loadData]);

  const docMap = useMemo(() => {
    const map = new Map<number, string>();
    for (const d of documents) {
      map.set(d.id, d.original_filename);
    }
    return map;
  }, [documents]);

  const filteredQuizzes = useMemo(() => {
    return quizzes.filter((q) => {
      if (docFilter !== "all" && q.document_id !== docFilter) return false;
      if (difficultyFilter !== "all" && q.difficulty !== difficultyFilter) return false;
      return true;
    });
  }, [quizzes, docFilter, difficultyFilter]);

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteQuiz(deleteTarget.id);
      setDeleteTarget(null);
      await loadData();
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
          <h1>Quizzes Hub</h1>
          <p>Browse, manage, and take quizzes generated from your study materials.</p>
        </div>
        <Link to="/create" className="btn primary">
          <PlusCircle size={16} />
          Create New Quiz
        </Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      {/* Stats row */}
      <div className="grid-three" style={{ marginBottom: "1.75rem" }}>
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#e0e7ff", color: "#4f46e5" }}>
            <Layers size={24} />
          </div>
          <div>
            <div className="stat-value">{quizzes.length}</div>
            <div className="stat-label">Total Generated Quizzes</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#dcfce7", color: "#16a34a" }}>
            <Play size={24} />
          </div>
          <div>
            <div className="stat-value">
              {quizzes.filter((q) => q.status === "ready").length}
            </div>
            <div className="stat-label">Ready to Practice</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#fef3c7", color: "#d97706" }}>
            <Sparkles size={24} />
          </div>
          <div>
            <div className="stat-value">
              {quizzes.reduce((acc, q) => acc + (q.questions?.length || q.requested_num_questions || 0), 0)}
            </div>
            <div className="stat-label">Total Questions Bank</div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "1.5rem" }}>
        <div className="row-between">
          <div className="row" style={{ gap: "1rem" }}>
            <div className="row" style={{ gap: "0.4rem" }}>
              <Filter size={15} style={{ color: "#64748b" }} />
              <span className="small muted">Filter:</span>
            </div>

            <div style={{ minWidth: "180px" }}>
              <select
                value={docFilter}
                onChange={(e) => setDocFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
                style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}
              >
                <option value="all">All Documents</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.original_filename}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ minWidth: "140px" }}>
              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                style={{ padding: "0.4rem 0.6rem", fontSize: "0.85rem" }}
              >
                <option value="all">All Difficulties</option>
                <option value="easy">Easy (Recall)</option>
                <option value="medium">Medium (Understanding)</option>
                <option value="hard">Hard (Analysis)</option>
              </select>
            </div>
          </div>

          {hasGenerating && (
            <span className="muted small row" style={{ gap: "0.4rem" }}>
              <Spinner dark /> Generating quiz in background…
            </span>
          )}
        </div>
      </div>

      {/* Quizzes List */}
      <section className="card">
        {loading ? (
          <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
            <Spinner dark />
            <p className="muted" style={{ marginTop: "0.75rem" }}>Loading quizzes…</p>
          </div>
        ) : filteredQuizzes.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3.5rem 1rem" }}>
            <HelpCircle size={48} style={{ color: "#cbd5e1", margin: "0 auto 1rem" }} />
            <h3>No quizzes found</h3>
            <p className="muted small" style={{ maxWidth: "420px", margin: "0 auto 1.5rem" }}>
              {quizzes.length === 0
                ? "You haven't generated any quizzes yet. Upload a document and generate your first AI study quiz."
                : "No quizzes match your selected filter criteria."}
            </p>
            {quizzes.length === 0 && (
              <Link to="/create" className="btn primary">
                Generate First Quiz <ArrowRight size={15} />
              </Link>
            )}
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Quiz</th>
                  <th>Source Document</th>
                  <th>Questions</th>
                  <th>Difficulty</th>
                  <th>LLM Mode</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredQuizzes.map((quiz) => {
                  const docName = docMap.get(quiz.document_id) || `Document #${quiz.document_id}`;
                  const numQ = quiz.questions?.length || quiz.requested_num_questions;
                  return (
                    <tr key={quiz.id}>
                      <td>
                        <strong>#{quiz.id}</strong>
                        {quiz.topic && (
                          <div className="small muted" style={{ marginTop: "0.15rem" }}>
                            Topic: {quiz.topic}
                          </div>
                        )}
                      </td>
                      <td>
                        <div className="row" style={{ gap: "0.4rem" }}>
                          <FileText size={15} style={{ color: "#6366f1" }} />
                          <span style={{ fontWeight: 500 }}>{docName}</span>
                        </div>
                      </td>
                      <td>
                        <span className="chip">{numQ} Qs</span>
                      </td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            background:
                              quiz.difficulty === "easy"
                                ? "#ecfdf5"
                                : quiz.difficulty === "medium"
                                ? "#eff6ff"
                                : "#fff1f2",
                            color:
                              quiz.difficulty === "easy"
                                ? "#065f46"
                                : quiz.difficulty === "medium"
                                ? "#1e40af"
                                : "#9f1239",
                            border: "1px solid rgba(0,0,0,0.06)",
                          }}
                        >
                          {quiz.difficulty}
                        </span>
                      </td>
                      <td>
                        <span className="small muted" style={{ textTransform: "capitalize" }}>
                          {quiz.mode}
                        </span>
                      </td>
                      <td>
                        <StatusBadge status={quiz.status} />
                        {quiz.error_message && (
                          <div className="small" style={{ color: "#ef4444", marginTop: "0.2rem", maxWidth: "200px" }}>
                            {quiz.error_message}
                          </div>
                        )}
                      </td>
                      <td className="small muted">{formatDateTime(quiz.created_at)}</td>
                      <td style={{ textAlign: "right" }}>
                        <div className="row" style={{ justifyContent: "flex-end", gap: "0.5rem" }}>
                          {quiz.status === "ready" && (
                            <Link to={`/quizzes/${quiz.id}`} className="btn primary sm">
                              <Play size={13} />
                              Practice
                            </Link>
                          )}
                          <button
                            type="button"
                            className="danger sm"
                            onClick={() => setDeleteTarget(quiz)}
                            title="Delete quiz"
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

      {/* Delete Modal Confirmation */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "#fee2e2", color: "#dc2626", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0 }}>Delete Quiz #{deleteTarget.id}?</h3>
                <span className="muted small">This will also delete associated attempt history.</span>
              </div>
            </div>

            <p className="small muted" style={{ marginBottom: "1.5rem" }}>
              Are you sure you want to delete this quiz generated from <strong>{docMap.get(deleteTarget.document_id) || `Document #${deleteTarget.document_id}`}</strong>? This action cannot be undone.
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
                {deleting ? <>Deleting… <Spinner /></> : "Yes, Delete Quiz"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  RotateCcw,
  BookOpen,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { QuizRead, SubmittedAnswer } from "../api/types";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { useMode } from "../state/ModeContext";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

interface AnswerDraft {
  selected_option: number | null;
  answer_text: string;
}

export default function TakeQuizPage() {
  const { quizId } = useParams();
  const id = Number(quizId);
  const navigate = useNavigate();
  const { mode } = useMode();

  const [quiz, setQuiz] = useState<QuizRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, AnswerDraft>>({});
  const [submitting, setSubmitting] = useState(false);
  const [showUnansweredConfirm, setShowUnansweredConfirm] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getQuiz(id);
      setQuiz(data);
      setError(null);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll while generating
  useEffect(() => {
    if (quiz?.status !== "generating") return;
    const timer = setInterval(() => void load(), 3000);
    return () => clearInterval(timer);
  }, [quiz?.status, load]);

  function updateAnswer(questionId: number, patch: Partial<AnswerDraft>) {
    setAnswers((current) => {
      const previous = current[questionId] ?? { selected_option: null, answer_text: "" };
      return { ...current, [questionId]: { ...previous, ...patch } };
    });
  }

  // Calculate answered questions
  const answeredStats = useMemo(() => {
    if (!quiz?.questions) return { answered: 0, total: 0, percent: 0, unansweredIndices: [] };
    const total = quiz.questions.length;
    let answered = 0;
    const unansweredIndices: number[] = [];

    quiz.questions.forEach((q, idx) => {
      const draft = answers[q.id];
      const isAnswered =
        q.type === "mcq"
          ? draft?.selected_option !== null && draft?.selected_option !== undefined
          : Boolean(draft?.answer_text?.trim());

      if (isAnswered) {
        answered += 1;
      } else {
        unansweredIndices.push(idx + 1);
      }
    });

    const percent = total > 0 ? Math.round((answered / total) * 100) : 0;
    return { answered, total, percent, unansweredIndices };
  }, [quiz?.questions, answers]);

  async function proceedSubmit() {
    if (!quiz) return;
    setSubmitting(true);
    setError(null);
    setShowUnansweredConfirm(false);

    const payload: SubmittedAnswer[] = quiz.questions.map((question) => {
      const draft = answers[question.id];
      if (question.type === "mcq") {
        return { question_id: question.id, selected_option: draft?.selected_option ?? null };
      }
      return { question_id: question.id, answer_text: draft?.answer_text ?? "" };
    });

    try {
      const attempt = await api.submitAttempt({ quiz_id: quiz.id, mode, answers: payload });
      navigate(`/attempts/${attempt.id}`);
    } catch (err) {
      setError(messageFor(err));
      setSubmitting(false);
    }
  }

  function handleCheckAndSubmit() {
    if (answeredStats.unansweredIndices.length > 0) {
      setShowUnansweredConfirm(true);
    } else {
      void proceedSubmit();
    }
  }

  function scrollToQuestion(index: number) {
    const el = document.getElementById(`question-card-${index}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  // 1. Initial Loading
  if (loading && !quiz) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "4rem 1rem" }}>
        <Spinner dark />
        <p className="muted" style={{ marginTop: "1rem" }}>Loading quiz data…</p>
      </div>
    );
  }

  // 2. Fatal Error and Not Found
  if (error && !quiz) {
    return (
      <>
        <div className="page-header">
          <h1>Quiz</h1>
        </div>
        <div className="alert error">
          <AlertCircle size={20} />
          <div>{error}</div>
        </div>
        <Link to="/quizzes" className="btn secondary">
          ← Back to Quizzes Hub
        </Link>
      </>
    );
  }

  // 3. Background Generation in Progress
  if (quiz?.status === "generating") {
    return (
      <>
        <div className="page-header">
          <div className="page-header-text">
            <h1>Generating Quiz #{quiz.id}</h1>
            <p>Our RAG pipeline is generating questions grounded in your document.</p>
          </div>
        </div>

        <div className="card" style={{ textAlign: "center", padding: "3.5rem 1.5rem" }}>
          <div style={{ marginBottom: "1.25rem" }}>
            <Spinner dark />
          </div>
          <h2 style={{ marginBottom: "0.5rem" }}>AI Quiz Authoring in Progress…</h2>
          <p className="muted small" style={{ maxWidth: "480px", margin: "0 auto 1.5rem" }}>
            Retrieving relevant chunks and constructing balanced questions with answer rubrics. On local CPU models, this may take a moment.
          </p>
          <div className="chip" style={{ display: "inline-flex", gap: "0.5rem", padding: "0.4rem 0.8rem" }}>
            <Clock size={14} /> Automatically refreshes every 3 seconds
          </div>
        </div>
      </>
    );
  }

  // 4. Generation Failed
  if (quiz?.status === "failed") {
    return (
      <>
        <div className="page-header">
          <h1>Quiz #{quiz.id}</h1>
        </div>
        <div className="alert error">
          <AlertCircle size={20} />
          <div>
            <strong>Quiz generation could not complete:</strong>
            <div style={{ marginTop: "0.3rem" }}>{quiz.error_message ?? "Unknown generation error"}</div>
          </div>
        </div>
        <div className="row" style={{ marginTop: "1rem" }}>
          <Link to="/create" className="btn primary">
            <RotateCcw size={15} /> Try Generating Again
          </Link>
          <Link to="/quizzes" className="btn secondary">
            Back to Quizzes
          </Link>
        </div>
      </>
    );
  }

  if (!quiz) return null;

  const optionLetters = ["A", "B", "C", "D"];

  return (
    <>
      {/* Quiz Top Banner */}
      <div className="quiz-header-banner">
        <div>
          <div className="row" style={{ gap: "0.6rem", marginBottom: "0.35rem" }}>
            <span style={{ fontSize: "1.45rem", fontWeight: 800 }}>Quiz #{quiz.id}</span>
            <StatusBadge status={quiz.status} />
          </div>
          <div style={{ color: "#cbd5e1", fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
            <span>{quiz.questions.length} Questions</span>
            <span>•</span>
            <span style={{ textTransform: "capitalize" }}>{quiz.difficulty} Difficulty</span>
            <span>•</span>
            <span style={{ textTransform: "capitalize" }}>Evaluated via {mode}</span>
            {quiz.topic && (
              <>
                <span>•</span>
                <span>Topic: <strong>{quiz.topic}</strong></span>
              </>
            )}
          </div>
        </div>

        <div>
          <button
            type="button"
            className="primary lg"
            onClick={handleCheckAndSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Spinner /> Evaluating with AI…
              </>
            ) : (
              <>
                <Send size={16} /> Submit Quiz
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sticky Question Navigator & Progress */}
      <div className="question-nav-strip">
        <div style={{ flex: 1, minWidth: "200px" }}>
          <div className="row-between" style={{ marginBottom: "0.4rem" }}>
            <span className="small muted">
              Progress: <strong>{answeredStats.answered}</strong> / {answeredStats.total} answered
            </span>
            <span className="small" style={{ fontWeight: 700, color: "var(--primary)" }}>
              {answeredStats.percent}%
            </span>
          </div>
          <div className="progress-track dark">
            <div className="progress-fill" style={{ width: `${answeredStats.percent}%` }} />
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginLeft: "1rem" }}>
          {quiz.questions.map((q, idx) => {
            const draft = answers[q.id];
            const isAnswered =
              q.type === "mcq"
                ? draft?.selected_option !== null && draft?.selected_option !== undefined
                : Boolean(draft?.answer_text?.trim());

            return (
              <button
                key={q.id}
                type="button"
                className={`nav-pill ${isAnswered ? "answered" : ""}`}
                onClick={() => scrollToQuestion(idx + 1)}
                title={`Jump to Question ${idx + 1}`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="alert error">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* Questions List */}
      {quiz.questions.map((question, qIdx) => {
        const draft = answers[question.id];
        const isAnswered =
          question.type === "mcq"
            ? draft?.selected_option !== null && draft?.selected_option !== undefined
            : Boolean(draft?.answer_text?.trim());

        return (
          <div
            key={question.id}
            id={`question-card-${qIdx + 1}`}
            className="question-card"
          >
            <div className="question-header">
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span className="question-number-badge">Q{qIdx + 1}</span>
                <span className="chip" style={{ textTransform: "capitalize" }}>
                  {question.type.replace("_", " ")}
                </span>
                {question.source_page_numbers && question.source_page_numbers.length > 0 && (
                  <span className="chip" style={{ color: "#4f46e5" }}>
                    <BookOpen size={12} /> Page / Slide {question.source_page_numbers.join(", ")}
                  </span>
                )}
              </div>

              {isAnswered && (
                <span className="small" style={{ color: "#10b981", display: "flex", alignItems: "center", gap: "0.3rem", fontWeight: 600 }}>
                  <CheckCircle2 size={15} /> Answered
                </span>
              )}
            </div>

            <h3 className="question-text">{question.text}</h3>

            {question.type === "mcq" && question.options ? (
              <div style={{ marginTop: "1.1rem" }}>
                {question.options.map((option, optIdx) => {
                  const isSelected = draft?.selected_option === optIdx;
                  return (
                    <div
                      key={optIdx}
                      className={`option-item ${isSelected ? "selected" : ""}`}
                      onClick={() => updateAnswer(question.id, { selected_option: optIdx })}
                    >
                      <div className="option-badge-key">
                        {optionLetters[optIdx] ?? optIdx + 1}
                      </div>
                      <span className="option-text">{option}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ marginTop: "1rem" }}>
                <textarea
                  placeholder={
                    question.type === "short_answer"
                      ? "Write a concise 1–3 sentence answer addressing the core concepts…"
                      : "Write a detailed, structured explanation covering all key aspects…"
                  }
                  value={draft?.answer_text ?? ""}
                  onChange={(e) => updateAnswer(question.id, { answer_text: e.target.value })}
                  style={{ minHeight: question.type === "long_answer" ? "140px" : "90px" }}
                />
                <div className="row-between" style={{ marginTop: "0.35rem" }}>
                  <span className="small muted">
                    Evaluated by AI against key points extracted from source material.
                  </span>
                  <span className="small muted">
                    {draft?.answer_text?.trim() ? `${draft.answer_text.trim().split(/\s+/).length} words` : "0 words"}
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Bottom Submit Bar */}
      <div
        className="card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1rem",
          marginTop: "2rem",
          background: "#ffffff",
        }}
      >
        <div>
          <div style={{ fontWeight: 700 }}>
            Ready to complete your attempt?
          </div>
          <div className="small muted">
            {answeredStats.answered === answeredStats.total
              ? "All questions answered. Submit to receive comprehensive feedback."
              : `${answeredStats.unansweredIndices.length} question(s) remaining.`}
          </div>
        </div>

        <button
          type="button"
          className="primary lg"
          onClick={handleCheckAndSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <>
              <Spinner /> Evaluating with AI…
            </>
          ) : (
            <>
              <Send size={16} /> Submit Quiz for Evaluation
            </>
          )}
        </button>
      </div>

      {/* Unanswered Questions Confirmation Modal */}
      {showUnansweredConfirm && (
        <div className="modal-overlay" onClick={() => setShowUnansweredConfirm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 12,
                  background: "#fffbeb",
                  color: "#d97706",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <AlertCircle size={22} />
              </div>
              <div>
                <h3 style={{ margin: 0 }}>Unanswered Questions</h3>
                <span className="muted small">
                  You have {answeredStats.unansweredIndices.length} unanswered question(s).
                </span>
              </div>
            </div>

            <p className="small muted" style={{ marginBottom: "1rem" }}>
              Questions <strong>#{answeredStats.unansweredIndices.join(", #")}</strong> do not have an answer yet. Unanswered questions receive 0 points.
            </p>

            <div className="row-between">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setShowUnansweredConfirm(false);
                  if (answeredStats.unansweredIndices[0]) {
                    scrollToQuestion(answeredStats.unansweredIndices[0]);
                  }
                }}
              >
                Review Questions
              </button>

              <button
                type="button"
                className="primary"
                onClick={() => void proceedSubmit()}
              >
                Submit Anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

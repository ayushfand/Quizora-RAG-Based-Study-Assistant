import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import confetti from "canvas-confetti";
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  Sparkles,
  BookOpen,
  ChevronDown,
  Printer,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { AnswerFeedback, AttemptRead } from "../api/types";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { scorePercent } from "../utils/format";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

function QuestionResultCard({ answer }: { answer: AnswerFeedback }) {
  const verdict = answer.verdict || "incorrect";
  const [modelOpen, setModelOpen] = useState(false);

  return (
    <div className={`question-card ${verdict}`}>
      <div className="question-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", flexWrap: "wrap" }}>
          <span className="question-number-badge">Q{answer.position}</span>
          <span className="chip" style={{ textTransform: "capitalize" }}>
            {answer.type.replace("_", " ")}
          </span>
          {answer.source_page_numbers && answer.source_page_numbers.length > 0 && (
            <span className="chip" style={{ color: "#4f46e5" }}>
              <BookOpen size={12} /> Page / Slide {answer.source_page_numbers.join(", ")}
            </span>
          )}
        </div>

        <div className="row" style={{ gap: "0.5rem" }}>
          <span className="small muted" style={{ fontWeight: 600 }}>
            {answer.score} / {answer.max_score} pts
          </span>
          <StatusBadge status={verdict} />
        </div>
      </div>

      <h3 className="question-text">{answer.text}</h3>

      {/* MCQ options review */}
      {answer.options && (
        <div style={{ marginTop: "1rem" }}>
          {answer.options.map((option, index) => {
            const isCorrect = index === answer.correct_option;
            const isSelected = index === answer.selected_option;

            let borderStyle = "1.5px solid var(--border)";
            let bgStyle = "var(--surface)";
            let textStyle = "var(--text-main)";

            if (isCorrect) {
              borderStyle = "1.5px solid #10b981";
              bgStyle = "#ecfdf5";
              textStyle = "#065f46";
            } else if (isSelected && !isCorrect) {
              borderStyle = "1.5px solid #ef4444";
              bgStyle = "#fef2f2";
              textStyle = "#991b1b";
            }

            return (
              <div
                key={index}
                className="option-item"
                style={{
                  border: borderStyle,
                  background: bgStyle,
                  cursor: "default",
                  color: textStyle,
                }}
              >
                <div
                  className="option-badge-key"
                  style={{
                    background: isCorrect ? "#10b981" : isSelected ? "#ef4444" : "var(--surface-subtle)",
                    color: isCorrect || isSelected ? "#ffffff" : "var(--text-muted)",
                    borderColor: isCorrect ? "#10b981" : isSelected ? "#ef4444" : "var(--border)",
                  }}
                >
                  {isCorrect ? <CheckCircle2 size={14} /> : isSelected ? <XCircle size={14} /> : String.fromCharCode(65 + index)}
                </div>
                <span className="option-text" style={{ fontWeight: isCorrect || isSelected ? 600 : 400 }}>
                  {option}
                  {isSelected && !isCorrect && <span style={{ fontSize: "0.8rem", marginLeft: "0.5rem" }}>(Your choice)</span>}
                  {isCorrect && isSelected && <span style={{ fontSize: "0.8rem", marginLeft: "0.5rem" }}>✔ (Your choice - Correct!)</span>}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Open-ended answer review */}
      {answer.type !== "mcq" && (
        <div style={{ marginTop: "1rem" }}>
          <div className="small label" style={{ color: "var(--text-muted)" }}>
            Your Answer:
          </div>
          <div
            style={{
              background: "#f8fafc",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              padding: "0.85rem 1rem",
              fontSize: "0.92rem",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}
          >
            {answer.user_answer ? (
              answer.user_answer
            ) : (
              <em className="muted">(No answer submitted — marked blank)</em>
            )}
          </div>
        </div>
      )}

      {/* Key Points Covered */}
      {answer.covered_points && answer.covered_points.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          <span className="small label" style={{ color: "#059669" }}>
            Key Points Covered:
          </span>
          <div className="row" style={{ gap: "0.4rem", marginTop: "0.25rem" }}>
            {answer.covered_points.map((pt, idx) => (
              <span
                key={idx}
                className="chip"
                style={{ background: "#ecfdf5", color: "#065f46", borderColor: "#a7f3d0" }}
              >
                <CheckCircle2 size={12} /> {pt}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Key Points Missed */}
      {answer.missed_points && answer.missed_points.length > 0 && (
        <div style={{ marginTop: "0.75rem" }}>
          <span className="small label" style={{ color: "#b91c1c" }}>
            Key Points Missed:
          </span>
          <div className="row" style={{ gap: "0.4rem", marginTop: "0.25rem" }}>
            {answer.missed_points.map((pt, idx) => (
              <span
                key={idx}
                className="chip"
                style={{ background: "#fef2f2", color: "#991b1b", borderColor: "#fecaca" }}
              >
                <XCircle size={12} /> {pt}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tutor Feedback */}
      {answer.feedback && (
        <div className="feedback-bubble info">
          <div style={{ fontWeight: 700, fontSize: "0.84rem", marginBottom: "0.25rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <Sparkles size={14} /> AI Evaluator Feedback:
          </div>
          {answer.feedback}
        </div>
      )}

      {/* Model Answer Toggle */}
      {answer.model_answer && (
        <div style={{ marginTop: "0.85rem" }}>
          <button
            type="button"
            className="ghost sm"
            onClick={() => setModelOpen(!modelOpen)}
            style={{ fontWeight: 600, color: "var(--primary)", padding: 0 }}
          >
            <ChevronDown
              size={15}
              style={{
                transform: modelOpen ? "rotate(180deg)" : "none",
                transition: "transform 0.2s ease",
              }}
            />
            {modelOpen ? "Hide Reference Model Answer" : "View Reference Model Answer"}
          </button>
          {modelOpen && (
            <div className="model-answer-box">
              <strong style={{ fontSize: "0.84rem", color: "var(--text-main)" }}>
                Reference Model Answer:
              </strong>
              <div style={{ marginTop: "0.35rem", lineHeight: 1.5 }}>{answer.model_answer}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  const { attemptId } = useParams();
  const id = Number(attemptId);
  const [attempt, setAttempt] = useState<AttemptRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confettiFired, setConfettiFired] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getAttempt(id);
        setAttempt(data);
      } catch (err) {
        setError(messageFor(err));
      }
    })();
  }, [id]);

  const percent = useMemo(() => {
    if (!attempt) return 0;
    return scorePercent(attempt.total_score, attempt.max_score);
  }, [attempt]);

  useEffect(() => {
    if (attempt && percent >= 75 && !confettiFired) {
      setConfettiFired(true);
      void confetti({
        particleCount: 90,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
  }, [attempt, percent, confettiFired]);

  const stats = useMemo(() => {
    if (!attempt) return { correct: 0, partial: 0, incorrect: 0, blank: 0 };
    let correct = 0;
    let partial = 0;
    let incorrect = 0;
    let blank = 0;

    for (const a of attempt.answers) {
      if (a.verdict === "correct") correct++;
      else if (a.verdict === "partial") partial++;
      else if (a.verdict === "blank") blank++;
      else incorrect++;
    }
    return { correct, partial, incorrect, blank };
  }, [attempt]);

  if (error) {
    return (
      <>
        <div className="page-header">
          <h1>Evaluation Result</h1>
        </div>
        <div className="alert error">{error}</div>
        <Link to="/history" className="btn secondary">
          ← Back to History
        </Link>
      </>
    );
  }

  if (!attempt) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "4rem 1rem" }}>
        <Spinner dark />
        <p className="muted" style={{ marginTop: "1rem" }}>Loading evaluation report…</p>
      </div>
    );
  }

  const getVerdictHeadline = () => {
    if (percent >= 90) return { title: "Outstanding Mastery! 🌟", text: "You demonstrated an exceptional grasp of the study material." };
    if (percent >= 75) return { title: "Great Performance! 🎯", text: "Solid understanding across core and supporting concepts." };
    if (percent >= 50) return { title: "Good Effort! 📚", text: "You have foundational knowledge, but some key areas need review." };
    return { title: "Review Recommended 💡", text: "Check the missed points and reference answers below to reinforce learning." };
  };

  const headline = getVerdictHeadline();

  return (
    <>
      <div className="page-header">
        <div className="page-header-text">
          <h1>Evaluation Report</h1>
          <p>
            Detailed AI-graded breakdown, rubric points analysis, and suggestions for improvement.
          </p>
        </div>
        <div className="row">
          <button
            type="button"
            className="secondary"
            onClick={() => window.print()}
            title="Print or save as PDF"
          >
            <Printer size={15} /> Print Report
          </button>
          <Link to={`/quizzes/${attempt.quiz_id}`} className="btn primary">
            <RotateCcw size={15} /> Retake Quiz
          </Link>
        </div>
      </div>

      {/* Hero Scorecard */}
      <section className="score-hero-container">
        <div className="score-hero-grid">
          <div>
            <span className="chip" style={{ background: "rgba(255,255,255,0.12)", color: "#ffffff", borderColor: "rgba(255,255,255,0.2)", marginBottom: "0.75rem" }}>
              Attempt #{attempt.id} · Evaluated via {attempt.mode}
            </span>
            <h2 style={{ color: "#ffffff", fontSize: "1.75rem", margin: "0.25rem 0 0.5rem" }}>
              {headline.title}
            </h2>
            <p style={{ color: "#cbd5e1", margin: 0, fontSize: "0.95rem" }}>
              {headline.text}
            </p>

            <div style={{ marginTop: "1.5rem" }}>
              <div className="row-between" style={{ color: "#cbd5e1", marginBottom: "0.4rem" }}>
                <span className="small">Overall Accuracy</span>
                <span className="small" style={{ fontWeight: 700, color: "#ffffff" }}>
                  {percent}%
                </span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${percent}%` }} />
              </div>
            </div>
          </div>

          <div style={{ textAlign: "center", background: "rgba(255,255,255,0.06)", borderRadius: "var(--radius-xl)", padding: "1.75rem", border: "1px solid rgba(255,255,255,0.1)" }}>
            <div className="score-big-number">{attempt.total_score}</div>
            <div style={{ color: "#cbd5e1", fontSize: "0.95rem", fontWeight: 600 }}>
              out of {attempt.max_score} total points
            </div>
            <div className="row" style={{ justifyContent: "center", gap: "0.6rem", marginTop: "1rem" }}>
              <span className="chip" style={{ background: "rgba(16, 185, 129, 0.2)", color: "#6ee7b7", borderColor: "transparent" }}>
                ✔ {stats.correct} Correct
              </span>
              {stats.partial > 0 && (
                <span className="chip" style={{ background: "rgba(245, 158, 11, 0.2)", color: "#fcd34d", borderColor: "transparent" }}>
                  ▲ {stats.partial} Partial
                </span>
              )}
              <span className="chip" style={{ background: "rgba(239, 68, 68, 0.2)", color: "#fca5a5", borderColor: "transparent" }}>
                ✘ {stats.incorrect + stats.blank} Missed
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Action links */}
      <div className="card" style={{ padding: "1rem 1.25rem", marginBottom: "2rem" }}>
        <div className="row-between">
          <span className="small muted">
            Review your answers question-by-question below, or practice with a new quiz.
          </span>
          <div className="row" style={{ gap: "0.75rem" }}>
            <Link to="/quizzes" className="btn secondary sm">
              All Quizzes
            </Link>
            <Link to="/create" className="btn primary sm">
              <Sparkles size={13} /> Create Another Quiz
            </Link>
          </div>
        </div>
      </div>

      {/* Per-Question Detailed Feedback */}
      <h2 style={{ marginBottom: "1.25rem" }}>Detailed Feedback by Question</h2>
      {attempt.answers.map((answer) => (
        <QuestionResultCard key={answer.question_id} answer={answer} />
      ))}
    </>
  );
}

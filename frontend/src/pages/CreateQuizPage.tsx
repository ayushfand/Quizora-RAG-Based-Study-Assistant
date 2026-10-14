import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  Sparkles,
  FileText,
  Sliders,
  Check,
  Play,
  BookOpen,
  AlertCircle,
  Zap,
  Cpu,
  Brain,
  Layers,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { Difficulty, DocumentRead, QuestionType, QuizRead } from "../api/types";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { useMode } from "../state/ModeContext";
import { formatDateTime } from "../utils/format";

interface TypeConfig {
  key: QuestionType;
  title: string;
  description: string;
  badge: string;
}

const QUESTION_TYPES: TypeConfig[] = [
  {
    key: "mcq",
    title: "Multiple Choice",
    description: "4 options with one verified answer and immediate objective grading.",
    badge: "Objective",
  },
  {
    key: "short_answer",
    title: "Short Answer",
    description: "1–3 sentences evaluated by AI using structured key-point rubrics.",
    badge: "AI-Evaluated",
  },
  {
    key: "long_answer",
    title: "Long Answer",
    description: "In-depth conceptual paragraphs with comprehensive feedback and model answers.",
    badge: "Deep Analysis",
  },
];

interface DifficultyConfig {
  key: Difficulty;
  title: string;
  level: string;
  desc: string;
  color: string;
}

const DIFFICULTIES: DifficultyConfig[] = [
  {
    key: "easy",
    title: "Easy",
    level: "Recall & Definition",
    desc: "Who, what, define, list, and identify foundational facts directly from the text.",
    color: "#10b981",
  },
  {
    key: "medium",
    title: "Medium",
    level: "Understanding & Application",
    desc: "Explain how, compare concepts, and illustrate with examples grounded in material.",
    color: "#4f46e5",
  },
  {
    key: "hard",
    title: "Hard",
    level: "Analysis & Synthesis",
    desc: "Multi-concept reasoning, evaluate trade-offs, and solve realistic scenarios.",
    color: "#ea580c",
  },
];

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export default function CreateQuizPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { mode } = useMode();

  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [documentId, setDocumentId] = useState<number | "">("");
  const [numQuestions, setNumQuestions] = useState(5);
  const [types, setTypes] = useState<QuestionType[]>(["mcq", "short_answer", "long_answer"]);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [topic, setTopic] = useState("");
  const [quizzes, setQuizzes] = useState<QuizRead[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const docs = await api.listDocuments();
        setDocuments(docs);
        const preselect = Number(searchParams.get("document_id"));
        const firstReady = docs.find((doc) => doc.status === "ready");
        if (preselect && docs.some((doc) => doc.id === preselect && doc.status === "ready")) {
          setDocumentId(preselect);
        } else if (firstReady) {
          setDocumentId(firstReady.id);
        }
      } catch (err) {
        setError(messageFor(err));
      } finally {
        setLoadingDocs(false);
      }
    })();
  }, [searchParams]);

  const loadQuizzes = useCallback(async (docId: number) => {
    try {
      setQuizzes(await api.listQuizzes(docId));
    } catch {
      setQuizzes([]);
    }
  }, []);

  useEffect(() => {
    if (documentId === "") {
      setQuizzes([]);
      return;
    }
    void loadQuizzes(documentId);
  }, [documentId, loadQuizzes]);

  const readyDocuments = useMemo(
    () => documents.filter((doc) => doc.status === "ready"),
    [documents],
  );

  const selectedDoc = useMemo(
    () => readyDocuments.find((d) => d.id === documentId),
    [readyDocuments, documentId],
  );

  function toggleType(type: QuestionType) {
    setTypes((current) => {
      if (current.includes(type)) {
        if (current.length === 1) return current; // Keep at least one
        return current.filter((t) => t !== type);
      }
      return [...current, type];
    });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (documentId === "") {
      setError("Please choose a study document first.");
      return;
    }
    if (types.length === 0) {
      setError("Pick at least one question type.");
      return;
    }
    if (numQuestions < 1 || numQuestions > 20) {
      setError("Number of questions must be between 1 and 20.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.generateQuiz({
        document_id: documentId,
        num_questions: numQuestions,
        question_types: types,
        difficulty,
        topic: topic.trim() ? topic.trim() : null,
        mode,
      });
      navigate(`/quizzes/${created.id}`);
    } catch (err) {
      setError(messageFor(err));
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div className="page-header-text">
          <h1>Generate AI Quiz</h1>
          <p>Configure question types, difficulty, and optional topic focus grounded in your documents.</p>
        </div>
      </div>

      {loadingDocs ? (
        <div className="card" style={{ textAlign: "center", padding: "3rem" }}>
          <Spinner dark />
          <p className="muted small" style={{ marginTop: "0.5rem" }}>Loading available documents…</p>
        </div>
      ) : readyDocuments.length === 0 ? (
        <div className="alert info">
          <BookOpen size={18} />
          <div>
            No processed documents available yet.{" "}
            <Link to="/" style={{ fontWeight: 600 }}>
              Upload your first study material
            </Link>{" "}
            to get started.
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="alert error">
              <AlertCircle size={18} />
              <div>{error}</div>
            </div>
          )}

          {/* Step 1: Select Document */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <FileText size={18} style={{ color: "#4f46e5" }} />
                1. Select Study Material
              </h2>
              {selectedDoc && (
                <span className="chip">
                  {selectedDoc.num_chunks ?? 0} indexed chunks
                </span>
              )}
            </div>

            <select
              id="document"
              value={documentId}
              onChange={(e) => setDocumentId(Number(e.target.value))}
              style={{ fontSize: "1rem", padding: "0.75rem 1rem" }}
            >
              {readyDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.original_filename} ({doc.num_chunks ?? 0} chunks)
                </option>
              ))}
            </select>
          </div>

          {/* Step 2: Question Types */}
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">
                  <Sliders size={18} style={{ color: "#4f46e5" }} />
                  2. Question Formats
                </h2>
                <div className="card-subtext">Choose one or mix multiple question formats for a balanced test.</div>
              </div>
            </div>

            <div className="choice-grid">
              {QUESTION_TYPES.map((qt) => {
                const isSelected = types.includes(qt.key);
                return (
                  <div
                    key={qt.key}
                    className={`choice-card ${isSelected ? "selected" : ""}`}
                    onClick={() => toggleType(qt.key)}
                  >
                    <div className="choice-card-header">
                      <span className="choice-card-title">{qt.title}</span>
                      <div
                        style={{
                          width: 22,
                          height: 22,
                          borderRadius: 6,
                          border: isSelected ? "none" : "1.5px solid #cbd5e1",
                          background: isSelected ? "var(--primary)" : "transparent",
                          color: "#ffffff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        {isSelected && <Check size={14} />}
                      </div>
                    </div>
                    <span className="chip" style={{ alignSelf: "flex-start", marginBottom: "0.4rem" }}>
                      {qt.badge}
                    </span>
                    <p className="choice-card-desc">{qt.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 3: Difficulty */}
          <div className="card">
            <div className="card-header">
              <div>
                <h2 className="card-title">
                  <Brain size={18} style={{ color: "#4f46e5" }} />
                  3. Difficulty & Cognitive Level
                </h2>
                <div className="card-subtext">Calibrate question complexity according to your study needs.</div>
              </div>
            </div>

            <div className="choice-grid">
              {DIFFICULTIES.map((diff) => {
                const isSelected = difficulty === diff.key;
                return (
                  <div
                    key={diff.key}
                    className={`choice-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setDifficulty(diff.key)}
                  >
                    <div className="choice-card-header">
                      <span className="choice-card-title" style={{ color: diff.color }}>
                        {diff.title}
                      </span>
                      {isSelected && (
                        <div
                          style={{
                            width: 18,
                            height: 18,
                            borderRadius: "50%",
                            background: "var(--primary)",
                            color: "#fff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <Check size={12} />
                        </div>
                      )}
                    </div>
                    <div style={{ fontWeight: 600, fontSize: "0.82rem", marginBottom: "0.3rem" }}>
                      {diff.level}
                    </div>
                    <p className="choice-card-desc">{diff.desc}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Step 4: Size & Topic Focus */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">
                <Zap size={18} style={{ color: "#4f46e5" }} />
                4. Quiz Scope & Specific Topic Focus
              </h2>
            </div>

            <div className="grid-two" style={{ marginBottom: "1.25rem" }}>
              <div>
                <label className="label" htmlFor="num-slider">
                  Number of Questions: <strong>{numQuestions}</strong>
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                  <input
                    id="num-slider"
                    type="range"
                    min={1}
                    max={20}
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    style={{ flex: 1, accentColor: "var(--primary)" }}
                  />
                  <span className="chip" style={{ fontSize: "0.9rem", padding: "0.3rem 0.75rem" }}>
                    {numQuestions} Qs
                  </span>
                </div>
                <div className="row" style={{ marginTop: "0.6rem", gap: "0.4rem" }}>
                  {[3, 5, 10, 15, 20].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className={`ghost sm ${numQuestions === preset ? "outline" : ""}`}
                      onClick={() => setNumQuestions(preset)}
                      style={{ padding: "0.25rem 0.55rem" }}
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="label" htmlFor="topic-input">
                  Topic Focus <span className="label-hint">(optional keyword focus)</span>
                </label>
                <input
                  id="topic-input"
                  type="text"
                  placeholder="e.g. thermodynamics, cell membrane, Section 3.2…"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
                <span className="small muted" style={{ display: "block", marginTop: "0.3rem" }}>
                  Leave blank to sample uniformly across the entire document.
                </span>
              </div>
            </div>

            {/* Submission Banner */}
            <div
              style={{
                background: "linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%)",
                border: "1px solid #c7d2fe",
                borderRadius: "var(--radius-lg)",
                padding: "1.25rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <div>
                <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>
                  Ready to Generate: {numQuestions} Questions · {difficulty.toUpperCase()}
                </div>
                <div className="small muted" style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginTop: "0.2rem" }}>
                  {mode === "local" ? <Cpu size={14} /> : <Sparkles size={14} />}
                  Using <strong>{mode === "local" ? "Local Ollama (Qwen 2.5)" : "Google Gemini"}</strong>
                </div>
              </div>

              <button type="submit" className="primary lg" disabled={submitting}>
                {submitting ? (
                  <>
                    <Spinner /> Generating Quiz…
                  </>
                ) : (
                  <>
                    <Sparkles size={18} /> Generate Quiz Now
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Quizzes generated for this document */}
      {documentId !== "" && quizzes.length > 0 && (
        <section className="card" style={{ marginTop: "2rem" }}>
          <div className="card-header">
            <div>
              <h2 className="card-title">
                <Layers size={18} style={{ color: "#4f46e5" }} />
                Previous Quizzes for This Material
              </h2>
              <div className="card-subtext">Past generated quizzes ready to practice again.</div>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Quiz #</th>
                  <th>Questions</th>
                  <th>Difficulty</th>
                  <th>Topic</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {quizzes.map((quiz) => (
                  <tr key={quiz.id}>
                    <td><strong>#{quiz.id}</strong></td>
                    <td>{quiz.requested_num_questions}</td>
                    <td><span className="chip">{quiz.difficulty}</span></td>
                    <td className="muted">{quiz.topic || "All topics"}</td>
                    <td className="small muted">{quiz.mode}</td>
                    <td><StatusBadge status={quiz.status} /></td>
                    <td className="small muted">{formatDateTime(quiz.created_at)}</td>
                    <td style={{ textAlign: "right" }}>
                      {quiz.status === "ready" ? (
                        <Link to={`/quizzes/${quiz.id}`} className="btn primary sm">
                          <Play size={13} /> Practice
                        </Link>
                      ) : (
                        <span className="muted small">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

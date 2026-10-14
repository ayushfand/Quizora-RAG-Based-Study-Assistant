import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  UploadCloud,
  FileText,
  Trash2,
  Sparkles,
  HelpCircle,
  AlertCircle,
  Database,
  Layers,
  CheckCircle2,
  X,
} from "lucide-react";
import { api, ApiError } from "../api/client";
import type { DocumentRead } from "../api/types";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { formatBytes, formatDateTime } from "../utils/format";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

const ALLOWED = [".pdf", ".pptx"];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentRead | null>(null);
  const [deleting, setDeleting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setDocuments(await api.listDocuments());
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

  const hasProcessing = useMemo(
    () => documents.some((doc) => doc.status === "processing"),
    [documents],
  );

  useEffect(() => {
    if (!hasProcessing) return;
    const timer = setInterval(() => void load(), 3000);
    return () => clearInterval(timer);
  }, [hasProcessing, load]);

  const totalChunks = useMemo(
    () => documents.reduce((acc, d) => acc + (d.num_chunks ?? 0), 0),
    [documents],
  );

  const readyCount = useMemo(
    () => documents.filter((d) => d.status === "ready").length,
    [documents],
  );

  function handleFileSelect(file: File | null) {
    if (!file) {
      setSelectedFile(null);
      return;
    }
    const lower = file.name.toLowerCase();
    if (!ALLOWED.some((ext) => lower.endsWith(ext))) {
      setError("Only PDF and PPTX files are supported.");
      setSelectedFile(null);
      return;
    }
    setError(null);
    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError("Please select a PDF or PPTX file first.");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(selectedFile);
      setSelectedFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await load();
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setUploading(false);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteDocument(deleteTarget.id);
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
          <h1>Study Materials</h1>
          <p>
            Upload course slides or textbooks. Our RAG engine extracts, chunks, and indexes every page for high-fidelity quizzes.
          </p>
        </div>
        {readyCount > 0 && (
          <Link to="/create" className="btn primary">
            <Sparkles size={16} />
            Generate Quiz
          </Link>
        )}
      </div>

      {error && (
        <div className="alert error">
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1 }}>{error}</div>
          <button className="ghost sm" onClick={() => setError(null)} style={{ padding: 0 }}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Stats Summary Cards */}
      <div className="grid-three" style={{ marginBottom: "1.75rem" }}>
        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#e0e7ff", color: "#4f46e5" }}>
            <FileText size={24} />
          </div>
          <div>
            <div className="stat-value">{documents.length}</div>
            <div className="stat-label">Uploaded Documents</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#dcfce7", color: "#16a34a" }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <div className="stat-value">{readyCount}</div>
            <div className="stat-label">Ready for Quizzes</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-wrap" style={{ background: "#f3e8ff", color: "#9333ea" }}>
            <Database size={24} />
          </div>
          <div>
            <div className="stat-value">{totalChunks}</div>
            <div className="stat-label">Indexed Vector Chunks</div>
          </div>
        </div>
      </div>

      {/* Drag & Drop Upload Zone */}
      <section className="card" style={{ padding: "1.75rem" }}>
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <UploadCloud size={20} style={{ color: "#4f46e5" }} />
              Upload Study Document
            </h2>
            <div className="card-subtext">
              Supports <strong>PDF</strong> and <strong>PPTX</strong> presentations (including PowerPoint speaker notes).
            </div>
          </div>
        </div>

        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.pptx"
          style={{ display: "none" }}
          onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
        />

        <div
          className={`dropzone ${isDragging ? "dragover" : ""}`}
          onClick={() => fileInput.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files?.[0]) {
              handleFileSelect(e.dataTransfer.files[0]);
            }
          }}
        >
          <div className="dropzone-icon-wrap">
            <UploadCloud size={28} />
          </div>
          <p className="dropzone-title">
            Drag & drop your study material here, or <span style={{ color: "var(--primary)" }}>browse files</span>
          </p>
          <p className="dropzone-desc">
            Maximum file size: 50 MB. Fast local vectorization with persistent ChromaDB.
          </p>
        </div>

        {selectedFile && (
          <div className="dropzone-file-preview">
            <FileText size={22} style={{ color: "#4f46e5", flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {selectedFile.name}
              </div>
              <div className="small muted">{formatBytes(selectedFile.size)}</div>
            </div>
            <button
              type="button"
              className="ghost sm"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                if (fileInput.current) fileInput.current.value = "";
              }}
              title="Cancel selection"
            >
              <X size={16} />
            </button>
            <button
              type="button"
              className="primary sm"
              onClick={(e) => {
                e.stopPropagation();
                handleUpload();
              }}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <Spinner /> Ingesting…
                </>
              ) : (
                <>
                  <UploadCloud size={14} /> Upload Now
                </>
              )}
            </button>
          </div>
        )}
      </section>

      {/* Documents Table */}
      <section className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">
              <Layers size={19} style={{ color: "#4f46e5" }} />
              Ingested Documents Library
            </h2>
            <div className="card-subtext">All parsed materials ready for grounding quiz questions.</div>
          </div>
          {hasProcessing && (
            <span className="muted small row" style={{ gap: "0.4rem" }}>
              <Spinner dark /> Ingesting in background…
            </span>
          )}
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
            <Spinner dark />
            <p className="muted small" style={{ marginTop: "0.5rem" }}>Loading documents…</p>
          </div>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: "center", padding: "3rem 1rem" }}>
            <HelpCircle size={44} style={{ color: "#cbd5e1", margin: "0 auto 0.75rem" }} />
            <h3>No study materials yet</h3>
            <p className="muted small" style={{ maxWidth: "380px", margin: "0 auto 1.25rem" }}>
              Upload your first lecture slide deck or PDF notes above to auto-generate custom quizzes.
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Type</th>
                  <th>File Size</th>
                  <th>Status</th>
                  <th>Chunks</th>
                  <th>Uploaded</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => {
                  const ext = doc.original_filename.split(".").pop()?.toUpperCase() || "DOC";
                  return (
                    <tr key={doc.id}>
                      <td>
                        <div className="row" style={{ gap: "0.6rem" }}>
                          <div
                            style={{
                              width: 32,
                              height: 32,
                              borderRadius: 8,
                              background: ext === "PDF" ? "#fee2e2" : "#ffedd5",
                              color: ext === "PDF" ? "#dc2626" : "#ea580c",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontWeight: 800,
                              fontSize: "0.72rem",
                              flexShrink: 0,
                            }}
                          >
                            {ext}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600 }}>{doc.original_filename}</div>
                            {doc.error_message && (
                              <div className="small" style={{ color: "#ef4444", marginTop: "0.2rem" }}>
                                {doc.error_message}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="chip">{doc.source_type || ext.toLowerCase()}</span>
                      </td>
                      <td>{formatBytes(doc.file_size)}</td>
                      <td>
                        <StatusBadge status={doc.status} />
                      </td>
                      <td>
                        {doc.num_chunks != null ? (
                          <span className="chip">{doc.num_chunks} chunks</span>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td className="small muted">{formatDateTime(doc.created_at)}</td>
                      <td style={{ textAlign: "right" }}>
                        <div className="row" style={{ justifyContent: "flex-end", gap: "0.5rem" }}>
                          {doc.status === "ready" && (
                            <Link to={`/create?document_id=${doc.id}`} className="btn primary sm">
                              <Sparkles size={13} />
                              Create Quiz
                            </Link>
                          )}
                          <button
                            type="button"
                            className="danger sm"
                            onClick={() => setDeleteTarget(doc)}
                            title="Delete document and vector index"
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
                <h3 style={{ margin: 0 }}>Delete Document?</h3>
                <span className="muted small">This action cannot be undone.</span>
              </div>
            </div>

            <p className="small muted" style={{ marginBottom: "1.5rem" }}>
              Are you sure you want to delete <strong>"{deleteTarget.original_filename}"</strong>? This will remove the file, all indexed ChromaDB chunks, and any associated quizzes.
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
                {deleting ? <>Deleting… <Spinner /></> : "Yes, Delete Document"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

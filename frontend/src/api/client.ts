// Thin fetch wrapper around the StudyQuiz AI backend.
//
// The dev server proxies /api to the backend, so the default base is relative.
// Set VITE_API_BASE_URL to point at a remote backend in production builds.

import type {
  AttemptCreate,
  AttemptRead,
  AttemptSummary,
  DocumentRead,
  HealthReport,
  QuizCreateResponse,
  QuizGenerateRequest,
  QuizRead,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the backend. Is the API server running?", 0);
  }

  if (!response.ok) {
    throw new ApiError(await extractError(response), response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function extractError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    /* fall through */
  }
  return `Request failed (HTTP ${response.status}).`;
}

export const api = {
  health: () => request<HealthReport>("/health"),

  listDocuments: () => request<DocumentRead[]>("/documents"),

  getDocument: (id: number) => request<DocumentRead>(`/documents/${id}`),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentRead>("/documents", { method: "POST", body: form });
  },

  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  generateQuiz: (payload: QuizGenerateRequest) =>
    request<QuizCreateResponse>("/quizzes/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getQuiz: (id: number) => request<QuizRead>(`/quizzes/${id}`),

  deleteQuiz: (id: number) => request<void>(`/quizzes/${id}`, { method: "DELETE" }),

  listQuizzes: (documentId?: number) =>
    request<QuizRead[]>(
      documentId != null ? `/quizzes?document_id=${documentId}` : "/quizzes",
    ),

  submitAttempt: (payload: AttemptCreate) =>
    request<AttemptRead>("/attempts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getAttempt: (id: number) => request<AttemptRead>(`/attempts/${id}`),

  deleteAttempt: (id: number) => request<void>(`/attempts/${id}`, { method: "DELETE" }),

  listAttempts: (quizId?: number) =>
    request<AttemptSummary[]>(
      quizId != null ? `/attempts?quiz_id=${quizId}` : "/attempts",
    ),
};

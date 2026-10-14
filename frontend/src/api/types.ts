// Shared API types — mirror the backend Pydantic schemas.

export type LlmMode = "local" | "gemini";
export type DocumentStatus = "processing" | "ready" | "failed";
export type QuizStatus = "generating" | "ready" | "failed";
export type QuestionType = "mcq" | "short_answer" | "long_answer";
export type Difficulty = "easy" | "medium" | "hard";
export type Verdict = "correct" | "partial" | "incorrect" | "blank";

export interface DocumentRead {
  id: number;
  original_filename: string;
  content_type: string;
  file_size: number;
  status: DocumentStatus;
  source_type: string | null;
  num_chunks: number | null;
  embedding_model: string | null;
  error_message: string | null;
  created_at: string;
}

export interface QuestionRead {
  id: number;
  position: number;
  type: QuestionType;
  difficulty: Difficulty;
  text: string;
  options: string[] | null;
  source_page_numbers: number[];
}

export interface QuizRead {
  id: number;
  document_id: number;
  requested_num_questions: number;
  question_types: string[];
  difficulty: Difficulty;
  topic: string | null;
  mode: string;
  status: QuizStatus;
  error_message: string | null;
  created_at: string;
  questions: QuestionRead[];
}

export interface QuizCreateResponse {
  id: number;
  status: QuizStatus;
}

export interface QuizGenerateRequest {
  document_id: number;
  num_questions: number;
  question_types: QuestionType[];
  difficulty: Difficulty;
  topic?: string | null;
  mode?: LlmMode | null;
}

export interface SubmittedAnswer {
  question_id: number;
  selected_option?: number | null;
  answer_text?: string | null;
}

export interface AttemptCreate {
  quiz_id: number;
  mode?: LlmMode | null;
  answers: SubmittedAnswer[];
}

export interface AnswerFeedback {
  question_id: number;
  position: number;
  type: QuestionType;
  text: string;
  options: string[] | null;
  correct_option: number | null;
  selected_option: number | null;
  user_answer: string;
  score: number;
  max_score: number;
  verdict: Verdict | "";
  covered_points: string[];
  missed_points: string[];
  feedback: string;
  model_answer: string | null;
  source_page_numbers: number[];
}

export interface AttemptRead {
  id: number;
  quiz_id: number;
  mode: string;
  total_score: number;
  max_score: number;
  created_at: string;
  answers: AnswerFeedback[];
}

export interface AttemptSummary {
  id: number;
  quiz_id: number;
  mode: string;
  total_score: number | null;
  max_score: number | null;
  created_at: string;
}

export interface ProviderHealth {
  mode: string;
  available: boolean;
  models: string[];
  default_model: string;
  default_model_available: boolean;
  error: string | null;
}

export interface HealthReport {
  status: "ok" | "degraded";
  database: { ok: boolean };
  llm: Record<string, ProviderHealth>;
  embeddings: ProviderHealth;
}

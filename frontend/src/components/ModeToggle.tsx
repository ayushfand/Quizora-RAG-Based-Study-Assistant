import { Cpu, Sparkles } from "lucide-react";
import { useMode } from "../state/ModeContext";

interface Props {
  geminiAvailable: boolean;
}

/** Local (Ollama) ↔ Google Gemini switch, persisted in localStorage via ModeContext. */
export default function ModeToggle({ geminiAvailable }: Props) {
  const { mode, setMode } = useMode();

  return (
    <div className="mode-toggle-segmented" role="group" aria-label="LLM mode">
      <button
        type="button"
        className={`mode-toggle-btn ${mode === "local" ? "active" : ""}`}
        onClick={() => setMode("local")}
        title="Local AI via Ollama (qwen2.5:7b-instruct)"
      >
        <Cpu size={14} />
        <span>Local Ollama</span>
      </button>

      <button
        type="button"
        className={`mode-toggle-btn ${mode === "gemini" ? "active" : ""}`}
        onClick={() => setMode("gemini")}
        title={
          geminiAvailable
            ? "Google Gemini 2.0 Flash (Cloud AI)"
            : "Gemini unavailable — configure GEMINI_API_KEY in backend/.env"
        }
      >
        <Sparkles size={14} />
        <span>Gemini{geminiAvailable ? "" : " ⚠"}</span>
      </button>
    </div>
  );
}

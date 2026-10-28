// LLM mode is a client-side preference persisted in localStorage and sent with
// quiz generation / attempt submission requests.

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { LlmMode } from "../api/types";

const STORAGE_KEY = "quizora.llmMode";

interface ModeContextValue {
  mode: LlmMode;
  setMode: (mode: LlmMode) => void;
  toggleMode: () => void;
}

const ModeContext = createContext<ModeContextValue | undefined>(undefined);

function readStoredMode(): LlmMode {
  const stored = localStorage.getItem(STORAGE_KEY) ?? localStorage.getItem("studyquiz.llmMode");
  return stored === "gemini" ? "gemini" : "local";
}

export function ModeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<LlmMode>(readStoredMode);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const setMode = useCallback((next: LlmMode) => setModeState(next), []);
  const toggleMode = useCallback(
    () => setModeState((current) => (current === "local" ? "gemini" : "local")),
    [],
  );

  const value = useMemo(() => ({ mode, setMode, toggleMode }), [mode, setMode, toggleMode]);
  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
}

export function useMode(): ModeContextValue {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error("useMode must be used inside a ModeProvider");
  }
  return context;
}

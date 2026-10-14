import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { BookOpen, Files, HelpCircle, PlusCircle, History } from "lucide-react";
import HealthIndicator from "./HealthIndicator";
import ModeToggle from "./ModeToggle";
import { useHealth } from "../hooks/useHealth";

export default function Layout({ children }: { children: ReactNode }) {
  const { health, loading, refresh } = useHealth();
  const geminiAvailable = Boolean(health?.llm.gemini.available);

  const getNavLinkClass = ({ isActive }: { isActive: boolean }) =>
    `nav-link ${isActive ? "active" : ""}`;

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <div className="brand-icon">
            <BookOpen size={19} />
          </div>
          <div>
            StudyQuiz <span className="gradient-text">AI</span>
          </div>
          <span className="badge-pill">RAG</span>
        </NavLink>

        <nav className="nav-links">
          <NavLink to="/" end className={getNavLinkClass}>
            <Files className="nav-link-icon" />
            <span>Documents</span>
          </NavLink>
          <NavLink to="/quizzes" className={getNavLinkClass}>
            <HelpCircle className="nav-link-icon" />
            <span>Quizzes</span>
          </NavLink>
          <NavLink to="/create" className={getNavLinkClass}>
            <PlusCircle className="nav-link-icon" />
            <span>Create Quiz</span>
          </NavLink>
          <NavLink to="/history" className={getNavLinkClass}>
            <History className="nav-link-icon" />
            <span>History</span>
          </NavLink>
        </nav>

        <div className="topbar-spacer" />

        <div className="topbar-right">
          <ModeToggle geminiAvailable={geminiAvailable} />
          <HealthIndicator health={health} loading={loading} onRefresh={refresh} />
        </div>
      </header>

      <main className="container">{children}</main>
    </div>
  );
}

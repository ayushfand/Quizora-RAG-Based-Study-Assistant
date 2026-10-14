import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Sparkles,
} from "lucide-react";

const CLASS_BY_STATUS: Record<string, string> = {
  ready: "ready",
  correct: "correct",
  processing: "processing",
  generating: "generating",
  partial: "partial",
  failed: "failed",
  incorrect: "incorrect",
  blank: "blank",
};

export default function StatusBadge({ status }: { status: string }) {
  const norm = status?.toLowerCase() || "processing";
  const badgeClass = CLASS_BY_STATUS[norm] ?? "processing";
  const label = norm.replace(/_/g, " ");

  const renderIcon = () => {
    switch (badgeClass) {
      case "ready":
      case "correct":
        return <CheckCircle2 size={13} />;
      case "processing":
      case "generating":
        return <Clock size={13} className="spin-slow" />;
      case "partial":
        return <AlertTriangle size={13} />;
      case "failed":
      case "incorrect":
        return <XCircle size={13} />;
      case "blank":
        return <HelpCircle size={13} />;
      default:
        return <Sparkles size={13} />;
    }
  };

  return (
    <span className={`badge ${badgeClass}`}>
      {renderIcon()}
      {label}
    </span>
  );
}

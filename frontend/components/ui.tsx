import { AlertTriangle, CheckCircle2, Circle, Info, XCircle, type LucideIcon } from "lucide-react";

export function PageHeader({ title, lead }: { title: string; lead: string }) {
  return (
    <header className="mb-8">
      <h1 className="h1">{title}</h1>
      <p className="lead">{lead}</p>
    </header>
  );
}

type State = "ok" | "warn" | "bad" | "info" | "todo";
const STATES: Record<State, { icon: LucideIcon; cls: string }> = {
  ok: { icon: CheckCircle2, cls: "border-ok/40 text-ok" },
  warn: { icon: AlertTriangle, cls: "border-warn/40 text-warn" },
  bad: { icon: XCircle, cls: "border-bad/40 text-bad" },
  info: { icon: Info, cls: "border-info/40 text-info" },
  todo: { icon: Circle, cls: "border-line text-muted" },
};

/** A status always shows an icon and words, never colour alone. */
export function Badge({ state, children }: { state: State; children: React.ReactNode }) {
  const { icon: Icon, cls } = STATES[state];
  return (
    <span className={`chip ${cls}`}>
      <Icon size={12} aria-hidden />
      {children}
    </span>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="mt-3 flex items-start gap-2 rounded-lg border border-bad/40 px-3 py-2 text-sm text-bad">
      <XCircle size={16} className="mt-0.5 shrink-0" aria-hidden />
      {message}
    </p>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-card border border-dashed border-line px-4 py-6 text-center text-sm text-muted">{children}</p>;
}

export function NeedsCandidate() {
  return (
    <Empty>
      Choose a candidate in the menu first. New candidates are onboarded in the Streamlit app
      (Onboard page) or by saving a resume there.
    </Empty>
  );
}

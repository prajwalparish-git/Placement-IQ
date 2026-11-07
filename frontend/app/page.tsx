"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Briefcase,
  Building2,
  Calculator,
  Cpu,
  FlaskConical,
  HardHat,
  HeartPulse,
  Landmark,
  Monitor,
  Scale,
  Wrench,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { get, type Catalog } from "@/lib/api";
import { useCandidate } from "@/lib/candidate";
import { ErrorNote, PageHeader } from "@/components/ui";

const ICONS: Record<string, LucideIcon> = {
  cs: Monitor,
  ece: Cpu,
  mech: Wrench,
  civil: HardHat,
  eee: Zap,
  biotech: FlaskConical,
  health: HeartPulse,
  commerce: Calculator,
  law: Scale,
  corp: Briefcase,
  govt_central: Landmark,
  govt_state: Building2,
};

export default function Home() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const { candidate } = useCandidate();

  useEffect(() => {
    get<Catalog>("/api/catalog").then(setCatalog, (e: Error) => setError(e.message));
  }, []);

  const roles = catalog?.domains.reduce((n, d) => n + d.roles.length, 0) ?? 0;
  const questions =
    catalog?.domains.reduce(
      (n, d) => n + d.topics.reduce((m, t) => m + Object.values(t.bank).reduce((a, b) => a + b, 0), 0),
      0,
    ) ?? 0;

  return (
    <>
      <PageHeader
        title={candidate ? `Welcome back, ${candidate.name}` : "Prepare for the role you want"}
        lead="Build an ATS-ready resume, practise with instant quizzes, rehearse a mock interview in your field, and follow a weekly plan that adapts to your scores."
      />

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Domains", catalog?.domains.length ?? "–"],
          ["Roles", roles || "–"],
          ["Practice questions", questions ? questions.toLocaleString() : "–"],
          ["Readiness", candidate ? `${candidate.readiness_score}/100` : "–"],
        ].map(([label, value]) => (
          <div key={label} className="card py-4">
            <p className="text-xs text-muted">{label}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-3 text-lg font-semibold">Career domains</h2>
      <ErrorNote message={error} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {catalog?.domains.map((d) => {
          const Icon = ICONS[d.id] ?? Briefcase;
          const expanded = open === d.id;
          return (
            <div key={d.id} className="card flex flex-col">
              <div className="flex items-start gap-3">
                <span className="rounded-lg bg-primary/10 p-2 text-primary-ink">
                  <Icon size={20} aria-hidden />
                </span>
                <div className="min-w-0">
                  <h3 className="font-semibold leading-snug">{d.name}</h3>
                  <p className="text-xs text-muted">
                    {d.roles.length} roles · {d.topics.length} topics
                  </p>
                </div>
              </div>
              <p className="mt-3 text-sm text-muted">{d.description}</p>
              <button
                type="button"
                className="mt-3 self-start text-sm font-medium text-primary-ink hover:underline"
                aria-expanded={expanded}
                onClick={() => setOpen(expanded ? null : d.id)}
              >
                {expanded ? "Hide roles" : "Show roles"}
              </button>
              {expanded && (
                <ul className="mt-2 space-y-1 text-sm">
                  {d.roles.map((r) => (
                    <li key={r.name}>
                      <Link
                        className="hover:underline"
                        href={`/resume-builder?domain=${d.id}&role=${encodeURIComponent(r.name)}`}
                      >
                        {r.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}

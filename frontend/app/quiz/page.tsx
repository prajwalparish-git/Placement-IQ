"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, Loader2, RotateCcw } from "lucide-react";
import { get, post, qs, type Graded, type Quiz } from "@/lib/api";
import { useCandidate } from "@/lib/candidate";
import { domainOf, useCatalog } from "@/lib/catalog";
import { Badge, ErrorNote, PageHeader } from "@/components/ui";

const LEVELS = ["easy", "medium", "hard"] as const;

export default function QuizPage() {
  const { catalog, error: catalogError } = useCatalog();
  const { candidate } = useCandidate();
  const [domainId, setDomainId] = useState<string>("");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState<string>("medium");
  const [count, setCount] = useState(5);
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [graded, setGraded] = useState<Graded | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // A candidate practises their own domain; a guest may pick any.
  const domain = useMemo(() => {
    if (!catalog) return null;
    if (candidate) return domainOf(catalog, candidate.target_role);
    return catalog.domains.find((d) => d.id === domainId) ?? catalog.domains[0];
  }, [catalog, candidate, domainId]);
  const topics = (domain?.topics ?? []).filter((t) => Object.keys(t.bank).length > 0);

  useEffect(() => {
    if (topics.length && !topics.some((t) => t.name === topic)) setTopic(topics[0].name);
  }, [topics, topic]);

  const available = topics.find((t) => t.name === topic)?.bank ?? {};

  async function start(level = difficulty) {
    setBusy(true);
    setError(null);
    setGraded(null);
    try {
      const q = await get<Quiz>(
        `/api/quiz?${qs({ topic, difficulty: level, count, candidate_id: candidate?.id })}`,
      );
      setQuiz(q);
      setDifficulty(level);
      setAnswers(q.questions.map(() => null));
    } catch (e) {
      setError((e as Error).message);
      setQuiz(null);
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!quiz) return;
    setBusy(true);
    setError(null);
    try {
      setGraded(
        await post<Graded>("/api/quiz/submit", {
          candidate_id: candidate?.id ?? null,
          topic: quiz.topic,
          difficulty: quiz.difficulty,
          answers: quiz.questions.map((q, i) => ({ id: q.id, choice: answers[i] })),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const blanks = answers.filter((a) => a === null).length;

  return (
    <>
      <PageHeader
        title="Quiz"
        lead={
          candidate
            ? `Questions from the bank for your domain, none you have answered before. Your score updates your weak topics and next week's plan.`
            : "Practise any domain as a guest; choose a candidate in the menu to save scores and track weak topics."
        }
      />
      <ErrorNote message={catalogError} />
      {catalog && topics.length === 0 && (
        <p className="mb-6 text-sm text-muted">
          No question bank is installed for this domain (data/questions/mcq_bank.csv). The Streamlit
          quiz still works: it generates questions.
        </p>
      )}

      <section className="card mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Quiz setup">
        {!candidate && (
          <div>
            <label className="label" htmlFor="domain">Domain</label>
            <select id="domain" className="input" value={domain?.id ?? ""} onChange={(e) => setDomainId(e.target.value)}>
              {catalog?.domains.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="label" htmlFor="topic">Topic</label>
          <select id="topic" className="input" value={topic} onChange={(e) => setTopic(e.target.value)}>
            {topics.map((t) => (
              <option key={t.name} value={t.name}>{t.name}</option>
            ))}
          </select>
        </div>
        <fieldset>
          <legend className="label">Difficulty</legend>
          <div className="flex rounded-lg border border-line p-0.5">
            {LEVELS.map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={difficulty === l}
                disabled={!available[l]}
                onClick={() => setDifficulty(l)}
                className={`flex-1 rounded-md px-2 py-1.5 text-sm capitalize disabled:opacity-40 ${
                  difficulty === l ? "bg-primary text-white" : "text-ink hover:bg-surface"
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </fieldset>
        <div>
          <label className="label" htmlFor="count">Questions</label>
          <select id="count" className="input" value={count} onChange={(e) => setCount(Number(e.target.value))}>
            {[5, 10, 15, 20].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <button type="button" className="btn-primary" disabled={!topic || busy} onClick={() => start()}>
            {busy && !quiz ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <ArrowRight size={16} aria-hidden />}
            Start quiz
          </button>
          <p className="ml-3 text-xs text-muted">
            {available[difficulty] ?? 0} {difficulty} questions in the bank for {topic || "this topic"}
            {candidate ? "; you get only those you have not answered" : ""}
          </p>
        </div>
      </section>

      <ErrorNote message={error} />

      {quiz && (
        <section aria-label="Questions" className="space-y-4">
          {graded && (
            <div className="card flex flex-wrap items-center gap-4">
              <p className="text-3xl font-semibold tabular-nums">{graded.score_pct}%</p>
              <p className="text-sm text-muted">
                {graded.correct} of {graded.total} correct · next suggested difficulty{" "}
                <span className="font-medium text-ink">{graded.next_difficulty}</span>
              </p>
              <div className="ml-auto flex gap-2">
                <button type="button" className="btn-ghost" onClick={() => start(difficulty)}>
                  <RotateCcw size={16} aria-hidden /> Same level
                </button>
                <button type="button" className="btn-primary" onClick={() => start(graded.next_difficulty)}>
                  Next quiz <ArrowRight size={16} aria-hidden />
                </button>
              </div>
            </div>
          )}

          {quiz.questions.map((q, i) => {
            const r = graded?.review[i];
            return (
              <fieldset key={q.id} className="card">
                <legend className="sr-only">Question {i + 1}</legend>
                <p className="font-medium">
                  <span className="mr-2 text-muted">Q{i + 1}.</span>
                  {q.text}
                </p>
                <div className="mt-3 grid gap-2">
                  {q.options.map((o, j) => {
                    const picked = answers[i] === j;
                    const right = r && j === r.correct_index;
                    const wrongPick = r && picked && !r.is_correct;
                    return (
                      <label
                        key={j}
                        className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2 text-sm ${
                          right ? "border-ok" : wrongPick ? "border-bad" : picked ? "border-primary" : "border-hair"
                        } ${graded ? "cursor-default" : "hover:bg-surface"}`}
                      >
                        <input
                          type="radio"
                          name={q.id}
                          className="mt-0.5 accent-[rgb(var(--primary))]"
                          checked={picked}
                          disabled={!!graded}
                          onChange={() => setAnswers((a) => a.map((x, k) => (k === i ? j : x)))}
                        />
                        <span className="flex-1">{o}</span>
                        {right && <Badge state="ok">Correct answer</Badge>}
                        {wrongPick && <Badge state="bad">Your answer</Badge>}
                      </label>
                    );
                  })}
                </div>
                {r && (
                  <p className="mt-3 text-sm text-muted">
                    {r.chosen === null && <Badge state="todo">Left blank</Badge>} {r.explanation}
                  </p>
                )}
              </fieldset>
            );
          })}

          {!graded && (
            <div className="flex items-center gap-3">
              <button type="button" className="btn-primary" disabled={busy} onClick={submit}>
                {busy ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <Check size={16} aria-hidden />}
                Submit answers
              </button>
              {blanks > 0 && <p className="text-sm text-muted">{blanks} left blank: they count as wrong.</p>}
            </div>
          )}
        </section>
      )}
    </>
  );
}

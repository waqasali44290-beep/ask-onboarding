// Onboarding journey: checklist with progress ring and badges, plus a quiz written from the documents.
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, messageOf } from "../api/client";
import { useUser } from "../auth";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import type { Journey, QuizItem } from "../types";

export default function OnboardingPage() {
  const user = useUser();
  const [journey, setJourney] = useState<Journey | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setJourney(await api.journey());
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggle(taskId: string, done: boolean) {
    // Update the screen at once; reload from the server if saving fails.
    setJourney((current) =>
      current && { ...current, tasks: current.tasks.map((t) => (t.id === taskId ? { ...t, done } : t)) },
    );
    try {
      await api.markTask(taskId, done);
    } catch {
      load();
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!journey) return <LoadingState label="Loading your journey…" />;

  const done = journey.tasks.filter((task) => task.done).length;
  const percent = Math.round((100 * done) / journey.tasks.length);
  const quizPassed = (journey.quiz_best ?? 0) >= journey.quiz_pass_percent;
  const badges = [
    { icon: "🚀", label: "First step", earned: done >= 1 },
    { icon: "⚡", label: "Halfway there", earned: percent >= 50 },
    { icon: "🏆", label: "All set", earned: percent === 100 },
    { icon: "🧠", label: "Quiz master", earned: quizPassed },
  ];

  return (
    <section className="page">
      <div className="journey-hero">
        <ProgressRing percent={percent} />
        <div>
          <h1 className="hero-title">Welcome aboard, {user.display_name.split(" ")[0]}!</h1>
          <p>
            {percent === 100
              ? "You've finished your onboarding checklist. 🎉"
              : `${done} of ${journey.tasks.length} steps done. Each step links to a question the assistant can answer.`}
          </p>
          <ul className="badges">
            {badges.map((badge) => (
              <li key={badge.label} className={badge.earned ? "badge-earned" : "badge-locked"} title={badge.earned ? "Earned" : "Not yet"}>
                <span aria-hidden="true">{badge.icon}</span> {badge.label}
                <span className="visually-hidden">{badge.earned ? " (earned)" : " (not yet earned)"}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <h2>Your checklist</h2>
      <ol className="checklist">
        {journey.tasks.map((task) => (
          <li key={task.id} className={task.done ? "task task-done" : "task"}>
            <input
              type="checkbox"
              id={`task-${task.id}`}
              checked={task.done}
              onChange={(event) => toggle(task.id, event.target.checked)}
            />
            <label htmlFor={`task-${task.id}`} className="task-text">
              <span className="task-title">{task.title}</span>
              <span className="muted">{task.description}</span>
            </label>
            <Link className="task-ask" to={`/chat?ask=${encodeURIComponent(task.ask)}`}>
              Ask the assistant →
            </Link>
          </li>
        ))}
      </ol>

      <h2>Test your knowledge</h2>
      <Quiz best={journey.quiz_best} passPercent={journey.quiz_pass_percent} onSaved={setJourney} />
    </section>
  );
}

function ProgressRing({ percent }: { percent: number }) {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="ring" role="img" aria-label={`${percent}% of onboarding done`}>
      <svg viewBox="0 0 100 100" width="112" height="112">
        <defs>
          <linearGradient id="ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#6d4aff" />
            <stop offset="100%" stopColor="#ec4899" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r={radius} className="ring-track" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          className="ring-value"
          stroke="url(#ring-gradient)"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - percent / 100)}
        />
      </svg>
      <span className="ring-label">{percent}%</span>
    </div>
  );
}

function Quiz({ best, passPercent, onSaved }: { best: number | null; passPercent: number; onSaved: (j: Journey) => void }) {
  const [items, setItems] = useState<QuizItem[] | null>(null);
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState<number | null>(null);
  const [correct, setCorrect] = useState(0);
  const [state, setState] = useState<"idle" | "loading" | "playing" | "finished">("idle");
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setState("loading");
    setError(null);
    try {
      const questions = await api.quiz();
      setItems(questions);
      setIndex(0);
      setChosen(null);
      setCorrect(0);
      setState(questions.length ? "playing" : "idle");
      if (!questions.length) setError("No quiz questions yet: they are written after documents are uploaded.");
    } catch (err) {
      setError(messageOf(err));
      setState("idle");
    }
  }

  function choose(option: number) {
    if (chosen !== null || !items) return;
    setChosen(option);
    if (option === items[index].answer) setCorrect((count) => count + 1);
  }

  async function next() {
    if (!items) return;
    if (index + 1 < items.length) {
      setIndex(index + 1);
      setChosen(null);
      return;
    }
    setState("finished");
    try {
      onSaved(await api.saveQuiz(correct, items.length));
    } catch {
      // the score is still shown; only saving the best score failed
    }
  }

  if (state === "loading") return <LoadingState label="Picking questions…" />;

  if (state === "playing" && items) {
    const item = items[index];
    return (
      <div className="quiz">
        <p className="quiz-progress">
          Question {index + 1} of {items.length}
        </p>
        <h3 className="quiz-question">{item.question}</h3>
        <div className="quiz-options">
          {item.options.map((option, optionIndex) => {
            const reveal = chosen !== null;
            const className = !reveal
              ? "quiz-option"
              : optionIndex === item.answer
                ? "quiz-option quiz-right"
                : optionIndex === chosen
                  ? "quiz-option quiz-wrong"
                  : "quiz-option";
            return (
              <button key={option} type="button" className={className} disabled={reveal} onClick={() => choose(optionIndex)}>
                <span className="quiz-letter">{"ABCD"[optionIndex]}</span> {option}
              </button>
            );
          })}
        </div>
        {chosen !== null && (
          <div className="quiz-feedback" role="status">
            <span>
              {chosen === item.answer ? "✅ Correct!" : "❌ Not quite."} Source: <strong>{item.filename}</strong>
            </span>
            <button type="button" className="button button-primary" onClick={next}>
              {index + 1 < items.length ? "Next question" : "See my score"}
            </button>
          </div>
        )}
      </div>
    );
  }

  if (state === "finished" && items) {
    const percent = Math.round((100 * correct) / items.length);
    return (
      <div className="quiz quiz-result">
        <p className="quiz-score">{percent}%</p>
        <p>
          {correct} of {items.length} correct.{" "}
          {percent >= passPercent ? "🧠 Quiz master badge earned!" : `Score ${passPercent}% to earn the Quiz master badge.`}
        </p>
        <button type="button" className="button button-primary" onClick={start}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="quiz">
      {error ? (
        <EmptyState title={error} />
      ) : (
        <p className="muted">
          A short quiz written by the assistant from the company documents.
          {best !== null && ` Your best score: ${best}%.`}
        </p>
      )}
      <button type="button" className="button button-primary" onClick={start}>
        {best === null ? "Start the quiz" : "Take it again"}
      </button>
    </div>
  );
}

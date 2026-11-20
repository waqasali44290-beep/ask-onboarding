// Login form, with one-click buttons for the demo accounts.
import { useState, type FormEvent } from "react";
import { messageOf } from "../api/client";
import { useAuth } from "../auth";

const DEMO_PASSWORD = "onboarding";
const DEMO_ACCOUNTS = [
  { username: "employee", label: "Employee" },
  { username: "manager", label: "Manager" },
  { username: "admin", label: "Help-desk admin" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signIn(name: string, secret: string) {
    setBusy(true);
    setError(null);
    try {
      await login(name, secret);
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    signIn(username, password);
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={handleSubmit}>
        <span className="brand-mark brand-mark-large" aria-hidden="true">
          A
        </span>
        <h1>Sign in to Ask Onboarding</h1>
        <p className="muted">Answers from the company handbook, wiki and IT guides.</p>

        <label htmlFor="username">Username</label>
        <input
          id="username"
          className="input"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          autoComplete="username"
          required
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          className="input"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button button-primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <div className="demo-accounts">
          <p className="muted">Demo accounts (password “{DEMO_PASSWORD}”):</p>
          <div className="demo-buttons">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                type="button"
                className="button"
                disabled={busy}
                onClick={() => signIn(account.username, DEMO_PASSWORD)}
              >
                {account.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
}

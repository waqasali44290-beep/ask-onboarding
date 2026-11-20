// Admin page: add users, change roles, set who reports to whom, reset passwords, deactivate.
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, messageOf } from "../api/client";
import { useUser } from "../auth";
import { ErrorState, LoadingState } from "../components/States";
import type { Role, UserAdmin, UserChange } from "../types";

const ROLES: { value: Role; label: string }[] = [
  { value: "employee", label: "Employee" },
  { value: "manager", label: "Manager" },
  { value: "admin", label: "Admin" },
];

export default function UsersPage() {
  const me = useUser();
  const [users, setUsers] = useState<UserAdmin[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setUsers(await api.listUsers());
    } catch (err) {
      setError(messageOf(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function change(user: UserAdmin, update: UserChange, done?: string) {
    setNotice(null);
    try {
      await api.updateUser(user.id, update);
      if (done) setNotice(done);
    } catch (err) {
      setNotice(messageOf(err));
    }
    load(); // team sizes and manager names may change too
  }

  function resetPassword(user: UserAdmin) {
    const password = window.prompt(`New password for ${user.display_name} (at least 8 characters):`);
    if (password) change(user, { password }, `Password reset for ${user.display_name}. They have been signed out.`);
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!users) return <LoadingState label="Loading users…" />;

  // Anyone active with a manager or admin role can have a team.
  const managers = users.filter((user) => user.is_active && user.role !== "employee");

  return (
    <section className="page page-wide">
      <h1>Users</h1>
      <p className="muted">
        Managers see their team's tickets; employees see only their own; admins see everything.
      </p>

      <NewUserForm managers={managers} onCreated={(name) => (setNotice(`${name} was added.`), load())} />

      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}

      <div className="table-scroll">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Reports to</th>
              <th className="numeric">Team</th>
              <th>Status</th>
              <th>
                <span className="visually-hidden">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const isMe = user.id === me.id;
              return (
                <tr key={user.id} className={user.is_active ? undefined : "row-inactive"}>
                  <td>
                    <span className="filename">{user.display_name}</span>
                    <p className="muted">
                      {user.username}
                      {isMe && " (you)"}
                    </p>
                  </td>
                  <td>
                    <select
                      className="input select select-small"
                      value={user.role}
                      disabled={isMe}
                      onChange={(event) => change(user, { role: event.target.value as Role })}
                      aria-label={`Role of ${user.display_name}`}
                    >
                      {ROLES.map((role) => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      className="input select select-small"
                      value={user.manager_id ?? ""}
                      onChange={(event) =>
                        change(user, { manager_id: event.target.value ? Number(event.target.value) : null })
                      }
                      aria-label={`Manager of ${user.display_name}`}
                    >
                      <option value="">— nobody —</option>
                      {managers
                        .filter((manager) => manager.id !== user.id)
                        .map((manager) => (
                          <option key={manager.id} value={manager.id}>
                            {manager.display_name}
                          </option>
                        ))}
                    </select>
                  </td>
                  <td className="numeric">{user.team_size || "–"}</td>
                  <td>
                    <span className={`badge ${user.is_active ? "badge-ready" : "badge-failed"}`}>
                      {user.is_active ? "Active" : "Deactivated"}
                    </span>
                  </td>
                  <td className="nowrap">
                    <button type="button" className="button button-quiet" onClick={() => resetPassword(user)}>
                      Reset password
                    </button>
                    {!isMe && (
                      <button
                        type="button"
                        className="button button-quiet"
                        onClick={() =>
                          (user.is_active
                            ? window.confirm(`Deactivate ${user.display_name}? They will be signed out and can't log in.`)
                            : true) && change(user, { is_active: !user.is_active })
                        }
                      >
                        {user.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function NewUserForm({ managers, onCreated }: { managers: UserAdmin[]; onCreated: (name: string) => void }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ display_name: "", username: "", role: "employee" as Role, password: "", manager_id: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (field: keyof typeof form) => (event: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.createUser({ ...form, manager_id: form.manager_id ? Number(form.manager_id) : null });
      onCreated(form.display_name);
      setForm({ display_name: "", username: "", role: "employee", password: "", manager_id: "" });
      setOpen(false);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className="button button-primary add-user" onClick={() => setOpen(true)}>
        + Add user
      </button>
    );
  }

  return (
    <form className="ticket user-form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Full name
          <input className="input" value={form.display_name} onChange={set("display_name")} required maxLength={100} />
        </label>
        <label>
          Username
          <input
            className="input"
            value={form.username}
            onChange={set("username")}
            required
            pattern="[A-Za-z0-9._\-]{2,50}"
            title="2–50 letters, numbers, dots, dashes or underscores"
            autoComplete="off"
          />
        </label>
        <label>
          Role
          <select className="input" value={form.role} onChange={set("role")}>
            {ROLES.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reports to
          <select className="input" value={form.manager_id} onChange={set("manager_id")}>
            <option value="">— nobody —</option>
            {managers.map((manager) => (
              <option key={manager.id} value={manager.id}>
                {manager.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Starting password
          <input
            className="input"
            type="password"
            value={form.password}
            onChange={set("password")}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
      </div>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      <div className="ticket-row">
        <button type="submit" className="button button-primary" disabled={saving}>
          {saving ? "Adding…" : "Add user"}
        </button>
        <button type="button" className="button button-quiet" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </form>
  );
}

import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { ChartIcon, ChatIcon, FileIcon, TicketIcon, UsersIcon } from "./components/Icons";
import Avatar from "./components/Avatar";
import { LoadingState } from "./components/States";
import AdminPage from "./pages/AdminPage";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import TicketsPage from "./pages/TicketsPage";
import UploadPage from "./pages/UploadPage";
import UsersPage from "./pages/UsersPage";

const ROLE_LABELS: Record<string, string> = { employee: "Employee", manager: "Manager", admin: "Admin" };
const TICKETS_LABEL: Record<string, string> = { employee: "My tickets", manager: "Team tickets", admin: "Tickets" };

export default function App() {
  const { user, checking, logout } = useAuth();

  if (checking) return <LoadingState label="Loading…" />;
  if (!user) return <LoginPage />;

  const isAdmin = user.role === "admin";
  return (
    <>
      <nav className="nav">
        <span className="brand">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          Ask Onboarding
        </span>
        <NavLink to="/chat">
          <ChatIcon /> Chat
        </NavLink>
        {isAdmin && (
          <NavLink to="/upload">
            <FileIcon /> Documents
          </NavLink>
        )}
        <NavLink to="/tickets">
          <TicketIcon /> {TICKETS_LABEL[user.role]}
        </NavLink>
        {isAdmin && (
          <NavLink to="/admin">
            <ChartIcon /> Admin
          </NavLink>
        )}
        {isAdmin && (
          <NavLink to="/users">
            <UsersIcon /> Users
          </NavLink>
        )}
        <span className="user-chip">
          <Avatar name={user.display_name} />
          <span className="user-text">
            <span className="user-name">{user.display_name}</span>
            <span className={`user-role role-${user.role}`}>{ROLE_LABELS[user.role] ?? user.role}</span>
          </span>
        </span>
        <button type="button" className="button button-quiet" onClick={logout}>
          Sign out
        </button>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          {isAdmin && <Route path="/upload" element={<UploadPage />} />}
          {isAdmin && <Route path="/admin" element={<AdminPage />} />}
          {isAdmin && <Route path="/users" element={<UsersPage />} />}
          <Route path="/tickets" element={<TicketsPage />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </main>
    </>
  );
}

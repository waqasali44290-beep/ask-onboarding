import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { ChatIcon, FileIcon, TicketIcon } from "./components/Icons";
import ChatPage from "./pages/ChatPage";
import TicketsPage from "./pages/TicketsPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
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
        <NavLink to="/upload">
          <FileIcon /> Documents
        </NavLink>
        <NavLink to="/tickets">
          <TicketIcon /> Tickets
        </NavLink>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/tickets" element={<TicketsPage />} />
        </Routes>
      </main>
    </>
  );
}

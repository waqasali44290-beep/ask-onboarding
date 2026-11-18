import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import UploadPage from "./pages/UploadPage";
import TicketsPage from "./pages/TicketsPage";

export default function App() {
  return (
    <>
      <nav className="nav">
        <strong>Ask Onboarding</strong>
        <NavLink to="/chat">Chat</NavLink>
        <NavLink to="/upload">Documents</NavLink>
        <NavLink to="/tickets">Tickets</NavLink>
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

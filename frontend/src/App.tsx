import { NavLink, Route, Routes } from "react-router-dom";
import { useActiveSession } from "./SessionContext";
import { NewSessionPage } from "./pages/NewSessionPage";
import { SessionHistoryPage } from "./pages/SessionHistoryPage";
import { AdministrationPage } from "./pages/AdministrationPage";
import { SessionEditorPage } from "./pages/SessionEditorPage";

export function App() {
  const { active } = useActiveSession();

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">✈ Booking Intent Detection</span>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            New Test Session
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
            Session History
          </NavLink>
          <NavLink to="/admin" className={({ isActive }) => (isActive ? "active" : "")}>
            Administration
          </NavLink>
        </nav>
        {active && (
          <span className="active-session-chip" title={active.id}>
            Active: {active.name || active.id.slice(0, 8)} ({active.mode})
          </span>
        )}
      </header>

      <main>
        <Routes>
          <Route path="/" element={<NewSessionPage />} />
          <Route path="/history" element={<SessionHistoryPage />} />
          <Route path="/admin" element={<AdministrationPage />} />
          <Route path="/session/:id" element={<SessionEditorPage />} />
        </Routes>
      </main>
    </div>
  );
}

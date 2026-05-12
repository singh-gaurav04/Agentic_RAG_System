import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import ChatPanel from "./components/ChatPanel";
import IngestionPanel from "./components/IngestionPanel";
import { getHealth } from "./services/api";

const createSessionId = () => `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const createSession = () => ({
  id: createSessionId(),
  title: "New chat",
  history: [],
});
const FALLBACK_SIDEBAR_TITLE = "New chat";

/** Max characters shown in sidebar for any title source. */
const truncateSidebarTitle = (text, maxLength = 34) => {
  const trimmed = text.trim();
  if (!trimmed) {
    return FALLBACK_SIDEBAR_TITLE;
  }
  return trimmed.length > maxLength ? `${trimmed.slice(0, maxLength)}...` : trimmed;
};

/** Backend-provided planner title wins when it's non-generic. */
const isUsefulSidebarTitle = (sessionTitle) => {
  if (sessionTitle === null || sessionTitle === undefined) {
    return false;
  }
  const trimmed = String(sessionTitle).trim();
  if (!trimmed) {
    return false;
  }
  const lower = trimmed.toLowerCase();
  const genericLabels = ["new chat", "untitled", "chat", "conversation"];
  if (genericLabels.includes(lower)) {
    return false;
  }
  return true;
};

const getSessionTitle = (history) => {
  const firstUserMessage = history.find((message) => message.role === "user");
  if (!firstUserMessage?.content) {
    return FALLBACK_SIDEBAR_TITLE;
  }
  const trimmedTitle = firstUserMessage.content.trim();
  if (!trimmedTitle) {
    return FALLBACK_SIDEBAR_TITLE;
  }
  return truncateSidebarTitle(trimmedTitle);
};

const resolveSidebarTitle = (sessionTitleFromBackend, history) => {
  if (isUsefulSidebarTitle(sessionTitleFromBackend)) {
    return truncateSidebarTitle(String(sessionTitleFromBackend).trim());
  }
  return getSessionTitle(history);
};

const navClass = ({ isActive }) =>
  [
    "block rounded-lg px-3 py-2 text-sm font-medium transition",
    isActive
      ? "bg-cyan-500/15 text-cyan-100 ring-1 ring-cyan-400/40"
      : "text-slate-300 hover:bg-slate-800/80 hover:text-white",
  ].join(" ");

function App() {
  const location = useLocation();
  const [healthStatus, setHealthStatus] = useState("Checking...");
  const [sessions, setSessions] = useState([createSession()]);
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0].id);
  const isChatRoute = location.pathname === "/";
  useEffect(() => {
    const fetchHealthStatus = async () => {
      try {
        const response = await getHealth();
        setHealthStatus(response?.status || "unknown");
      } catch (error) {
        setHealthStatus("offline");
      }
    };
    fetchHealthStatus();
  }, []);
  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0];
  const handleCreateNewChat = () => {
    const newSession = createSession();
    setSessions((previousSessions) => [newSession, ...previousSessions]);
    setActiveSessionId(newSession.id);
  };
  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId);
  };
  const handleSessionHistoryChange = (history, meta = {}) => {
    if (!activeSession) {
      return;
    }
    const backendTitle =
      meta && typeof meta === "object"
        ? meta.session_title ?? meta.sessionTitle
        : undefined;
    setSessions((previousSessions) =>
      previousSessions.map((session) =>
        session.id === activeSession.id
          ? {
              ...session,
              history,
              title: resolveSidebarTitle(backendTitle, history),
            }
          : session
      )
    );
  };

  return (
    <main className="relative h-screen overflow-hidden bg-[#0f1117] text-slate-100">
      <div className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-10 h-72 w-72 rounded-full bg-violet-500/10 blur-3xl" />
      <div className="flex h-full w-full overflow-hidden">
        <aside className="hidden w-72 flex-col border-r border-slate-800/70 bg-[#12151d]/90 backdrop-blur md:flex">
          <div className="border-b border-slate-800/70 p-5">
            <h1 className="text-lg font-semibold tracking-tight">Skyclad Ventures</h1>
            <p className="mt-1 text-xs text-slate-400">AI-powered Research Assistant</p>
          </div>
          <nav className="space-y-1 border-b border-slate-800/70 px-3 py-4">
            <NavLink end className={navClass} to="/">
              Chat
            </NavLink>
            <NavLink className={navClass} to="/ingest-papers">
              Ingest papers
            </NavLink>
          </nav>
          {isChatRoute ? (
            <>
              <div className="p-4">
                <button
                  className="w-full rounded-xl border border-cyan-400/20 bg-gradient-to-r from-cyan-500/20 to-violet-500/20 px-3 py-2 text-sm font-medium transition hover:scale-[1.02] hover:from-cyan-500/30 hover:to-violet-500/30"
                  onClick={handleCreateNewChat}
                  type="button"
                >
                  + New chat
                </button>
              </div>
              <div className="hide-scrollbar flex-1 space-y-2 overflow-y-auto px-3 pb-3">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    className={`w-full truncate rounded-xl px-3 py-2 text-left text-sm transition ${
                      session.id === activeSessionId
                        ? "glass-card text-white shadow-md shadow-cyan-500/10"
                        : "bg-slate-900/70 text-slate-300 hover:bg-slate-800/80"
                    }`}
                    onClick={() => handleSelectSession(session.id)}
                    type="button"
                  >
                    {session.title}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 px-3 py-4">
              <p className="rounded-lg border border-slate-700/80 bg-slate-900/50 p-3 text-xs leading-relaxed text-slate-400">
                Index arXiv papers into Pinecone via{" "}
                <code className="text-cyan-200/90">POST /ingest-papers</code>. Use the form in the main
                panel when you are connected to the API.
              </p>
            </div>
          )}
          <div className="mt-auto flex flex-col justify-between border-t border-slate-800/70 p-4 text-xs text-slate-400">
            Backend: {healthStatus === "ok" ? "connected ✅" : "failed to connect ❌"}
            <span className="mt-1 text-[10px] text-slate-400">made by Gaurav singh </span>
          </div>
        </aside>
        <section className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex border-b border-slate-800/70 bg-[#12151d]/80 px-3 py-2 md:hidden">
            <nav className="flex flex-1 gap-2">
              <NavLink end className={navClass} to="/">
                Chat
              </NavLink>
              <NavLink className={navClass} to="/ingest-papers">
                Ingest
              </NavLink>
            </nav>
          </div>
          <Routes>
            <Route
              path="/"
              element={
                <>
                  <header className="flex h-14 flex-col justify-center border-b border-slate-800/70 bg-[#12151d]/60 px-5 backdrop-blur">
                    <p className="text-sm font-medium tracking-wide text-slate-200">{activeSession.title}</p>
                    <p className="text-[10px] text-slate-400">{activeSession.id}</p>
                  </header>
                  <div className="min-h-0 flex-1">
                    <ChatPanel
                      sessionId={activeSession.id}
                      history={activeSession.history}
                      onHistoryChange={handleSessionHistoryChange}
                    />
                  </div>
                </>
              }
            />
            <Route
              path="/ingest-papers"
              element={
                <>
                  <header className="flex h-14 flex-col justify-center border-b border-slate-800/70 bg-[#12151d]/60 px-5 backdrop-blur md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm font-medium tracking-wide text-slate-200">Paper ingestion</p>
                      <p className="text-[10px] text-slate-400">
                        Mirrors backend route <span className="text-cyan-200/90">POST /ingest-papers</span> · arXiv
                        → Pinecone
                      </p>
                    </div>
                  </header>
                  <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
                    <IngestionPanel />
                  </div>
                </>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </section>
      </div>
    </main>
  );
}

export default App;

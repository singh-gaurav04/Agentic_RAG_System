import { useEffect, useState } from "react";
import ChatPanel from "./components/ChatPanel";
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
function App() {
  const [healthStatus, setHealthStatus] = useState("Checking...");
  const [sessions, setSessions] = useState([createSession()]);
  const [activeSessionId, setActiveSessionId] = useState(sessions[0].id);
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
          <div className="mt-auto border-t border-slate-800/70 p-4 text-xs text-slate-400 flex justify-between  flex-col">
            Backend: {healthStatus==="ok" ? "connected ✅" : "failed to connect ❌"}
            <span className="text-[10px] text-slate-400">made by Gaurav singh </span>
          </div>
        </aside>
        <section className="flex min-w-0 flex-1 flex-col">
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
        </section>
      </div>
    </main>
  );
}
export default App;

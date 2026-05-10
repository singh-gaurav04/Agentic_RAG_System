import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { normalizeChatError, sendChatMessage } from "../services/api";

const markdownComponents = {
  code({ inline, children, ...props }) {
    if (inline) {
      return (
        <code className="rounded bg-slate-800 px-1.5 py-0.5 text-[0.9em] text-cyan-100" {...props}>
          {children}
        </code>
      );
    }
    return (
      <pre className="my-3 overflow-x-auto rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm leading-relaxed">
        <code className="text-slate-100" {...props}>
          {children}
        </code>
      </pre>
    );
  },
  h1({ children, ...props }) {
    return (
      <h1 className="mb-3 mt-4 border-b border-slate-700 pb-2 text-2xl font-semibold tracking-tight text-slate-50" {...props}>
        {children}
      </h1>
    );
  },
  h2({ children, ...props }) {
    return (
      <h2 className="mb-2 mt-5 text-lg font-semibold text-slate-100" {...props}>
        {children}
      </h2>
    );
  },
  h3({ children, ...props }) {
    return (
      <h3 className="mb-2 mt-4 text-base font-semibold text-slate-200" {...props}>
        {children}
      </h3>
    );
  },
  p({ children, ...props }) {
    return (
      <p className="mb-3 last:mb-0 leading-relaxed text-slate-100" {...props}>
        {children}
      </p>
    );
  },
  ul({ children, ...props }) {
    return (
      <ul className="mb-3 ml-6 list-disc space-y-2 text-slate-100 marker:text-slate-500" {...props}>
        {children}
      </ul>
    );
  },
  ol({ children, ...props }) {
    return (
      <ol className="mb-3 ml-6 list-decimal space-y-2 text-slate-100 marker:text-slate-500" {...props}>
        {children}
      </ol>
    );
  },
  li({ children, ...props }) {
    return (
      <li className="leading-relaxed" {...props}>
        {children}
      </li>
    );
  },
  blockquote({ children, ...props }) {
    return (
      <blockquote className="my-3 border-l-4 border-violet-500/60 bg-slate-900/60 py-2 pl-4 italic text-slate-300" {...props}>
        {children}
      </blockquote>
    );
  },
  a({ children, ...props }) {
    return (
      <a className="font-medium text-cyan-300 underline underline-offset-2 hover:text-cyan-200" target="_blank" rel="noreferrer" {...props}>
        {children}
      </a>
    );
  },
  hr() {
    return <hr className="my-4 border-slate-700" />;
  },
  table({ children, ...props }) {
    return (
      <div className="my-3 overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full border-collapse text-left text-sm text-slate-100" {...props}>
          {children}
        </table>
      </div>
    );
  },
  thead({ children, ...props }) {
    return <thead className="bg-slate-900/90 text-xs uppercase tracking-wide text-slate-400" {...props}>{children}</thead>;
  },
  tbody({ children, ...props }) {
    return <tbody className="divide-y divide-slate-800 bg-slate-950/80" {...props}>{children}</tbody>;
  },
  th({ children, ...props }) {
    return (
      <th className="px-3 py-2 font-semibold text-slate-200" {...props}>
        {children}
      </th>
    );
  },
  td({ children, ...props }) {
    return (
      <td className="px-3 py-2 text-slate-200" {...props}>
        {children}
      </td>
    );
  },
};

/**
 * Collapsible retrieval sources anchored at the bottom of an assistant turn.
 *
 * @param {{ references?: Array<{ paper_id?: string, title?: string, source_url?: string, section?: string }> }} props
 */
function MessageReferencesCollapse({ references }) {
  const [open, setOpen] = useState(false);
  if (!references || references.length === 0) {
    return null;
  }
  return (
    <div className="mt-3 border-t border-slate-700/70 pt-3">
      <button
        type="button"
        aria-expanded={open}
        aria-label={open ? "Hide references" : "Show references"}
        onClick={() => setOpen(!open)}
        className="group flex w-full items-center gap-2 rounded-lg px-1 py-1.5 text-left text-xs font-medium text-slate-400 transition hover:bg-slate-800/50 hover:text-slate-200"
      >
        <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-600 bg-slate-900 text-sm font-semibold leading-none text-cyan-300 transition group-hover:border-cyan-500/60 group-hover:bg-slate-800">
          {open ? "−" : "+"}
        </span>
        <span className="text-slate-300">
          Sources <span className="text-slate-500">({references.length})</span>
        </span>
      </button>
      {open ? (
        <ul className="mt-2 space-y-1.5 rounded-lg border border-slate-700/60 bg-slate-950/50 px-3 py-2">
          {references.map((ref, idx) => (
            <li key={`${ref.paper_id}-${idx}`} className="text-sm leading-snug text-slate-300">
              <a className="text-cyan-400 hover:text-cyan-300" href={ref.source_url} target="_blank" rel="noreferrer">
                {ref.title || ref.paper_id}
              </a>
              {ref.section ? <span className="text-slate-500"> · {ref.section}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function ChatPanel({ sessionId, history, onHistoryChange }) {
  const [query, setQuery] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [errorBanner, setErrorBanner] = useState({ kind: "error", message: "" });
  const messagesEndReference = useRef(null);
  useEffect(() => {
    messagesEndReference.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, isSending]);
  useEffect(() => {
    setQuery("");
    setErrorBanner({ kind: "error", message: "" });
    setIsSending(false);
  }, [sessionId]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }
    setIsSending(true);
    setErrorBanner({ kind: "error", message: "" });
    const previousHistorySnapshot = [...history];
    const userMessage = { role: "user", content: trimmedQuery };
    const nextHistory = [...history, userMessage];
    onHistoryChange(nextHistory);
    setQuery("");
    try {
      const response = await sendChatMessage({ session_id: sessionId, user_query: trimmedQuery });
      const refs = Array.isArray(response.references) ? response.references : [];
      const sessionTitleFromApi = response.session_title ?? response.sessionTitle ?? null;
      onHistoryChange(
        [
          ...nextHistory,
          {
            role: "assistant",
            content: response.answer ?? "",
            references: refs.length > 0 ? refs : undefined,
          },
        ],
        { session_title: sessionTitleFromApi }
      );
    } catch (error) {
      const normalized = normalizeChatError(error);
      setErrorBanner({ kind: normalized.kind, message: normalized.message });
      onHistoryChange(previousHistorySnapshot);
    } finally {
      setIsSending(false);
    }
  };

  const handleComposerKeyDown = (event) => {
    if (event.key !== "Enter") {
      return;
    }
    if (event.shiftKey) {
      return;
    }
    event.preventDefault();
    if (isSending || !query.trim()) {
      return;
    }
    const formElement = event.currentTarget.closest("form");
    formElement?.requestSubmit();
  };

  const showError = Boolean(errorBanner.message);
  const isRateLimited = errorBanner.kind === "rate_limit";

  return (
    <section className="flex h-full flex-col bg-[#0f1117]">
      <div className="hide-scrollbar mx-auto w-full max-w-4xl flex-1 overflow-y-auto px-4 py-8">
        {!history.length ? (
          <div className="fade-in mt-20 text-center">
            <h2 className="bg-gradient-to-r from-cyan-300 to-violet-300 bg-clip-text text-4xl font-semibold text-transparent">
              How can I help you today?
            </h2>
            <p className="mt-2 text-sm text-slate-400">Session: {sessionId}</p>
          </div>
        ) : null}
        {history.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`fade-in mb-5 flex items-start gap-3 ${message.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            <div
              className={`mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${
                message.role === "user" ? "bg-cyan-500/20 text-cyan-200" : "bg-violet-500/20 text-violet-200"
              }`}
              aria-hidden="true"
            >
              {message.role === "user" ? "🙂" : "🤖"}
            </div>
            <div
              className={`rounded-2xl px-4 py-3 text-[15px] leading-relaxed shadow-md ${
                message.role === "user"
                  ? "max-w-[88%] border border-cyan-400/20 bg-gradient-to-br from-cyan-500/15 to-cyan-400/5 text-slate-100"
                  : "glass-card w-full text-slate-100"
              }`}
            >
              {message.role === "assistant" ? (
                <>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {typeof message.content === "string" ? message.content : String(message.content ?? "")}
                  </ReactMarkdown>
                  <MessageReferencesCollapse references={message.references} />
                </>
              ) : (
                message.content
              )}
            </div>
          </div>
        ))}
        {isSending ? (
          <div className="fade-in glass-card mb-5 w-full rounded-2xl px-4 py-3 text-[15px] text-slate-300">
            <span className="loading-dots">Thinking</span>
          </div>
        ) : null}
        <div ref={messagesEndReference} />
      </div>
      {showError ? (
        <div
          className={`mx-auto mb-3 w-full max-w-3xl rounded-lg border p-3 text-sm leading-relaxed ${
            isRateLimited
              ? "border-amber-700/80 bg-amber-950/50 text-amber-100"
              : "border-rose-800 bg-rose-950/60 text-rose-200"
          }`}
        >
          <p className="font-semibold">{isRateLimited ? "Too many requests" : "Something went wrong"}</p>
          <p className="mt-1 opacity-95">
            {isRateLimited
              ? "The model or API stopped this request due to rate limits. Wait a short time and try again, or shorten your prompt."
              : errorBanner.message}
          </p>

        </div>
      ) : null}
      <form className="border-t border-slate-800/70 bg-[#0f1117]/95 p-3 backdrop-blur" onSubmit={handleSendMessage}>
        <div className="glass-card mx-auto flex w-full max-w-4xl items-end gap-2 rounded-2xl p-2">
          <textarea
            className="max-h-24 min-h-10 w-full resize-none bg-transparent px-2 py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500"
            placeholder="ask ai anything related to ai or cs.AI"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleComposerKeyDown}
          />
          <button
            className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-cyan-300 to-violet-300 text-black transition hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50"
            type="submit"
            disabled={isSending || !query.trim()}
            aria-label="Send message"
          >
            ↑
          </button>
        </div>
      </form>
    </section>
  );
}

export default ChatPanel;

import { useEffect, useState } from "react";
import { ingestPapers } from "../services/api";

const DEFAULT_FORM_STATE = {
  max_papers: 20,
  category: "cs.AI",
  days_back: 90,
  batch_size: 10,
};

const PIPELINE_STEPS = [
  "Pulling recent arXiv metadata…",
  "Resolving PDF URLs and queue…",
  "Downloading & parsing papers…",
  "Chunking text for retrieval…",
  "Embedding with Mistral…",
  "Upserting vectors to Pinecone…",
];

const CATEGORY_LABELS = {
  "cs.AI": "Artificial Intelligence",
  "cs.CV": "Computer Vision",
  "cs.LG": "Machine Learning",
  "cs.CL": "Computation & Language",
  "cs.SE": "Software Engineering",
  "cs.DS": "Data Structures",
};

const getErrorMessage = (error) => error?.response?.data?.detail || error?.message || "Request failed";

function IngestionLoadingOverlay({ stepIndex }) {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-6 rounded-2xl bg-[#0b0e14]/82 px-6 py-10 backdrop-blur-md"
    >
      <div className="relative flex h-28 w-28 items-center justify-center">
        <div
          className="ingest-orbit-outer absolute h-full w-full rounded-full border-2 border-transparent border-t-cyan-400/80 border-r-violet-400/50"
          aria-hidden
        />
        <div
          className="ingest-orbit-inner absolute h-[70%] w-[70%] rounded-full border-2 border-transparent border-b-emerald-400/70 border-l-cyan-300/40"
          aria-hidden
        />
        <div className="flex items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/20 to-violet-600/20 p-4 ring-1 ring-cyan-400/30">
          <svg className="h-10 w-10 text-cyan-200" fill="none" viewBox="0 0 24 24" aria-hidden>
            <path
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M4 7a3 3 0 013-3h10a3 3 0 013 3v10a3 3 0 01-3 3H7a3 3 0 01-3-3V7z M8 11h8M8 15h5"
            />
          </svg>
        </div>
      </div>
      <div className="flex gap-1.5" aria-hidden>
        <span className="ingest-particle-0 h-2 w-2 rounded-full bg-cyan-400" />
        <span className="ingest-particle-1 h-2 w-2 rounded-full bg-violet-400" />
        <span className="ingest-particle-2 h-2 w-2 rounded-full bg-emerald-400" />
      </div>
      <p
        key={stepIndex}
        className="ingest-step-text max-w-sm text-center text-sm font-medium tracking-wide text-slate-200"
      >
        {PIPELINE_STEPS[stepIndex]}
      </p>
      <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-slate-800/90 ring-1 ring-slate-700/80">
        <div className="ingest-shimmer-bar h-full" />
      </div>
      <p className="text-center text-[11px] uppercase tracking-[0.22em] text-slate-500">Indexing in progress</p>
    </div>
  );
}

function IngestionPanel() {
  const [formData, setFormData] = useState(DEFAULT_FORM_STATE);
  const [responseData, setResponseData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!isLoading) {
      setStepIndex(0);
      return undefined;
    }
    const id = window.setInterval(() => {
      setStepIndex((previous) => (previous + 1) % PIPELINE_STEPS.length);
    }, 2100);
    return () => window.clearInterval(id);
  }, [isLoading]);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    const numericFields = new Set(["max_papers", "days_back", "batch_size"]);
    setFormData((previousState) => ({
      ...previousState,
      [name]: numericFields.has(name) ? Number(value) : value,
    }));
  };

  const handleIngestPapers = async (event) => {
    event.preventDefault();
    setIsLoading(true);
    setErrorMessage("");
    try {
      const response = await ingestPapers(formData);
      setResponseData(response);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsLoading(false);
    }
  };

  const inputClasses =
    "mt-1.5 w-full rounded-xl border border-slate-600/60 bg-slate-950/50 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-500/50 focus:ring-2 focus:ring-cyan-500/25 disabled:cursor-not-allowed disabled:opacity-50";

  const labelClasses = "group block text-xs font-medium uppercase tracking-wider text-slate-500";

  const categoryLabel = CATEGORY_LABELS[formData.category] ?? formData.category;

  return (
    <div className="relative mx-auto max-w-3xl">
      <div className="pointer-events-none absolute -left-8 -top-8 h-36 w-36 rounded-full bg-cyan-500/10 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-6 -right-4 h-40 w-40 rounded-full bg-violet-500/10 blur-2xl" />
      <section
        className={`relative overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-b from-[#1a1f2e]/95 to-[#12151f]/98 p-6 shadow-2xl shadow-black/40 backdrop-blur-sm sm:p-8 ${
          isLoading ? "ingest-card-glow" : ""
        }`}
      >
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent"
          aria-hidden
        />
        {isLoading ? <IngestionLoadingOverlay stepIndex={stepIndex} /> : null}
        <div className={isLoading ? "pointer-events-none opacity-[0.35] blur-[0.5px] transition" : "transition"}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/25 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest text-cyan-200/90">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-40" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan-400" />
                </span>
                Corpus ingest
              </div>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Index arXiv papers</h2>
              <p className="mt-2 max-w-lg text-sm leading-relaxed text-slate-400">
                Streams papers from arXiv into your Pinecone namespace. Each run deduplicates by{" "}
                <code className="rounded-md bg-slate-800/80 px-1.5 py-0.5 text-xs text-cyan-200/90">paper_id</code> on
                the server.
              </p>
            </div>
            <div className="flex shrink-0 flex-col gap-2 rounded-xl border border-slate-700/50 bg-slate-900/40 p-4 text-right sm:min-w-[200px]">
              <span className="text-[10px] uppercase tracking-widest text-slate-500">Active profile</span>
              <span className="text-lg font-semibold text-slate-100">{formData.max_papers} papers</span>
              <span className="text-sm text-violet-300/90">{categoryLabel}</span>
              <span className="text-xs text-slate-500">
                Last {formData.days_back} days · batches of {formData.batch_size}
              </span>
            </div>
          </div>
          <form className="mt-8 space-y-6" onSubmit={handleIngestPapers}>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className={labelClasses}>
                Max papers
                <input
                  className={inputClasses}
                  disabled={isLoading}
                  type="number"
                  min="1"
                  max="200"
                  name="max_papers"
                  value={formData.max_papers}
                  onChange={handleInputChange}
                />
              </label>
              <label className={labelClasses}>
                arXiv category
                <select
                  className={`${inputClasses} cursor-pointer`}
                  disabled={isLoading}
                  name="category"
                  value={formData.category}
                  onChange={handleInputChange}
                >
                  {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {value} — {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className={labelClasses}>
                Date window (days)
                <input
                  className={inputClasses}
                  disabled={isLoading}
                  type="number"
                  min="1"
                  max="365"
                  name="days_back"
                  value={formData.days_back}
                  onChange={handleInputChange}
                />
              </label>
              <label className={labelClasses}>
                Batch size
                <input
                  className={inputClasses}
                  disabled={isLoading}
                  type="number"
                  min="1"
                  max="50"
                  name="batch_size"
                  value={formData.batch_size}
                  onChange={handleInputChange}
                />
              </label>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-slate-500">
                Endpoint{" "}
                <code className="rounded bg-slate-800/90 px-2 py-1 text-[11px] text-emerald-300/90">POST</code>{" "}
                <code className="rounded bg-slate-800/90 px-2 py-1 text-[11px] text-cyan-200/80">/ingest-papers</code>
              </p>
              <button
                className="group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-cyan-600 via-cyan-500 to-violet-600 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-cyan-900/30 transition hover:scale-[1.02] hover:shadow-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100 sm:min-w-[200px]"
                disabled={isLoading}
                type="submit"
              >
                <span className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/12 to-white/0 opacity-0 transition group-hover:opacity-100" />
                <svg className="relative h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" aria-hidden>
                  <path
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4"
                  />
                </svg>
                <span className="relative">Start ingestion</span>
              </button>
            </div>
          </form>
        </div>
        {errorMessage ? (
          <div
            className="fade-in mt-6 rounded-xl border border-rose-500/35 bg-gradient-to-r from-rose-950/50 to-red-950/30 px-4 py-3 text-sm text-rose-100"
            role="alert"
          >
            <p className="font-medium text-rose-200">Something went wrong</p>
            <p className="mt-1 text-rose-100/90">{errorMessage}</p>
          </div>
        ) : null}
        <div className="fade-in mt-8 rounded-xl border border-slate-700/50 bg-slate-950/50 p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
            <h3 className="text-sm font-semibold text-slate-200">Latest run</h3>
            {responseData &&
            typeof responseData.indexed === "number" &&
            typeof responseData.requested === "number" ? (
              <div className="flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 font-medium text-emerald-300 ring-1 ring-emerald-400/25">
                  Indexed {responseData.indexed}/{responseData.requested}
                </span>
                {typeof responseData.failed === "number" && responseData.failed > 0 ? (
                  <span className="rounded-full bg-amber-500/15 px-2.5 py-1 font-medium text-amber-200 ring-1 ring-amber-400/25">
                    Failed {responseData.failed}
                  </span>
                ) : null}
                {typeof responseData.skipped_duplicates === "number" && responseData.skipped_duplicates > 0 ? (
                  <span className="rounded-full bg-slate-500/20 px-2.5 py-1 text-slate-300 ring-1 ring-slate-500/25">
                    Skipped {responseData.skipped_duplicates} dupes
                  </span>
                ) : null}
              </div>
            ) : (
              <span className="text-[11px] text-slate-500">No completed run yet</span>
            )}
          </div>
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-slate-800/90 bg-[#0a0c10] p-4 font-mono text-[11px] leading-relaxed text-slate-300">
            {JSON.stringify(responseData || { message: "Submit the form to see the API response here." }, null, 2)}
          </pre>
        </div>
      </section>
    </div>
  );
}

export default IngestionPanel;

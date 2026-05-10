import { useState } from "react";
import { ingestPapers } from "../services/api";
const DEFAULT_FORM_STATE = {
  max_papers: 20,
  category: "cs.AI",
  days_back: 90,
  batch_size: 10,
};
const getErrorMessage = (error) => error?.response?.data?.detail || error?.message || "Request failed";
function IngestionPanel() {
  const [formData, setFormData] = useState(DEFAULT_FORM_STATE);
  const [responseData, setResponseData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
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
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-800">Ingestion</h2>
      <p className="mt-1 text-sm text-slate-500">Trigger arXiv indexing jobs from the UI.</p>
      <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={handleIngestPapers}>
        <label className="text-sm text-slate-600">
          Max Papers
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 outline-none ring-blue-500 focus:ring-2"
            type="number"
            min="1"
            max="200"
            name="max_papers"
            value={formData.max_papers}
            onChange={handleInputChange}
          />
        </label>
        <label className="text-sm text-slate-600">
          Category
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 outline-none ring-blue-500 focus:ring-2"
            name="category"
            value={formData.category}
            onChange={handleInputChange}
          >
            <option value="cs.AI">cs.AI</option>
            <option value="cs.CV">cs.CV</option>
            <option value="cs.LG">cs.LG</option>
            <option value="cs.CL">cs.CL</option>
            <option value="cs.SE">cs.SE</option>
            <option value="cs.DS">cs.DS</option>
          </select>
        </label>
        <label className="text-sm text-slate-600">
          Days Back
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 outline-none ring-blue-500 focus:ring-2"
            type="number"
            min="1"
            max="365"
            name="days_back"
            value={formData.days_back}
            onChange={handleInputChange}
          />
        </label>
        <label className="text-sm text-slate-600">
          Batch Size
          <input
            className="mt-1 w-full rounded-lg border border-slate-300 p-2 outline-none ring-blue-500 focus:ring-2"
            type="number"
            min="1"
            max="50"
            name="batch_size"
            value={formData.batch_size}
            onChange={handleInputChange}
          />
        </label>
        <div className="sm:col-span-2">
          <button
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? "Ingesting..." : "Ingest Papers"}
          </button>
        </div>
      </form>
      {errorMessage ? (
        <p className="mt-3 rounded-lg bg-rose-50 p-2 text-sm text-rose-700">{errorMessage}</p>
      ) : null}
      <div className="mt-4 rounded-lg border border-slate-200 p-3">
        <h3 className="font-medium text-slate-700">Latest Ingestion Result</h3>
        <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
          {JSON.stringify(responseData || {}, null, 2)}
        </pre>
      </div>
    </section>
  );
}
export default IngestionPanel;

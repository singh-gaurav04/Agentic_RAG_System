import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 600000,
});

/**
 * Normalize FastAPI `{ detail }`, plain strings, axios errors, and provider rate messages.
 *
 * @param {unknown} error
 * @returns {{ message: string, kind: "rate_limit" | "error" }}
 */
export const normalizeChatError = (error) => {
  /** @type {number | undefined} */
  let status = undefined;
  /** @type {unknown} */
  let detailPayload = undefined;
  if (error && typeof error === "object" && "response" in error && error.response) {
    status = /** @type {{ status?: number }} */ (error.response).status;
    detailPayload = /** @type {{ data?: { detail?: unknown } }} */ (error.response).data?.detail;
  }
  /** @type {string} */
  let raw = "";
  if (typeof detailPayload === "string") {
    raw = detailPayload;
  } else if (detailPayload !== undefined && typeof detailPayload === "object" && detailPayload !== null && "msg" in detailPayload) {
    raw = String(/** @type {{ msg?: string }} */ (detailPayload).msg ?? "");
  } else if (detailPayload !== undefined) {
    try {
      raw = JSON.stringify(detailPayload);
    } catch {
      raw = String(detailPayload);
    }
  }
  if (!raw.trim() && error instanceof Error && error.message) {
    raw = error.message;
  }
  if (!raw.trim()) {
    raw = typeof error === "string" ? error : "Request failed";
  }
  const lower = raw.toLowerCase();
  const isRate =
    status === 429 ||
    lower.includes("rate limit") ||
    lower.includes("too many requests") ||
    /\b429\b/.test(lower) ||
    lower.includes("throttle") ||
    lower.includes("throttl");

  return {
    message: raw,
    kind: isRate ? "rate_limit" : "error",
  };
};

/**
 * Backend contract: `{ session_id: string, user_query: string }` — history can merge via checkpoints when same session_id.
 */
export const sendChatMessage = async ({ session_id, user_query }) => {
  const response = await apiClient.post("/chat", { session_id, user_query });
  return response.data;
};

export const ingestPapers = async (payload) => {
  const response = await apiClient.post("/ingest-papers", payload);
  return response.data;
};

export const getHealth = async () => {
  const response = await apiClient.get("/health");
  return response.data;
};

const STORAGE_KEY = "trustops_api_base_url";
const DEFAULT_LOCAL = "http://localhost:8001";

function normalizeUrl(url) {
  if (!url) return "";
  return String(url).trim().replace(/\/$/, "");
}

export function isGithubPagesHost() {
  if (typeof window === "undefined") return false;
  return window.location.hostname.endsWith("github.io");
}

export function isLocalDevHost() {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

export function getStoredApiBaseUrl() {
  if (typeof window === "undefined") return "";
  return normalizeUrl(localStorage.getItem(STORAGE_KEY));
}

export function setStoredApiBaseUrl(url) {
  const normalized = normalizeUrl(url);
  if (normalized) {
    localStorage.setItem(STORAGE_KEY, normalized);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
  return normalized;
}

export function getBuildApiBaseUrl() {
  return normalizeUrl(import.meta.env.VITE_API_BASE_URL || "");
}

/** Apply ?api=https://host:8001 from the URL and persist for this browser. */
export function initApiConfigFromUrl() {
  if (typeof window === "undefined") return;
  const fromQuery = normalizeUrl(new URLSearchParams(window.location.search).get("api"));
  if (!fromQuery) return;
  setStoredApiBaseUrl(fromQuery);
  const url = new URL(window.location.href);
  url.searchParams.delete("api");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

export function getApiBaseUrl() {
  const stored = getStoredApiBaseUrl();
  if (stored) return stored;
  const built = getBuildApiBaseUrl();
  if (built) return built;
  return DEFAULT_LOCAL;
}

/** True when the UI is hosted remotely but still points at localhost. */
export function usesMisconfiguredApi() {
  const active = getApiBaseUrl();
  if (!active.includes("localhost") && !active.includes("127.0.0.1")) {
    return false;
  }
  return isGithubPagesHost() || !isLocalDevHost();
}

export function getApiConnectionErrorMessage() {
  if (usesMisconfiguredApi()) {
    return (
      "TrustOps API is not configured for this hosted UI. " +
      "Set the VITE_API_BASE_URL build variable, open with ?api=https://YOUR_API, " +
      "or run locally at http://localhost:5173."
    );
  }
  return `Cannot reach the TrustOps API at ${getApiBaseUrl()}. Is the backend running and reachable from this device?`;
}

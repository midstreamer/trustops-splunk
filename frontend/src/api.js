/**
 * TrustOps API client. Base URL from runtime config, build env, or localhost.
 */

import {
  getApiBaseUrl,
  getApiConnectionErrorMessage,
  initApiConfigFromUrl,
} from "./apiConfig.js";

initApiConfigFromUrl();

const baseUrl = () => getApiBaseUrl();

async function request(path, options = {}) {
  const url = `${baseUrl()}${path.startsWith("/") ? path : `/${path}`}`;
  const init = {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  };
  let res;
  try {
    res = await fetch(url, init);
  } catch (err) {
    const msg =
      err instanceof TypeError ? getApiConnectionErrorMessage() : String(err?.message || err);
    throw new Error(msg);
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }
  if (!res.ok) {
    let detail = data?.detail ?? data?.message ?? res.statusText;
    if (Array.isArray(detail)) {
      detail = detail
        .map((d) => (typeof d === "object" && d?.msg ? d.msg : JSON.stringify(d)))
        .join("; ");
    } else if (detail && typeof detail !== "string") {
      detail = JSON.stringify(detail);
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return data;
}

export function getHealth() {
  return request("/health");
}

export function getAlerts() {
  return request("/alerts");
}

export function getInvestigation(alertId) {
  return request(`/alerts/${encodeURIComponent(alertId)}/investigation`);
}

export function getAgentPlan(alertId) {
  return request(`/alerts/${encodeURIComponent(alertId)}/agent-plan`);
}

export function getAgentRun(alertId) {
  return request(`/alerts/${encodeURIComponent(alertId)}/agent-run`);
}

export function postAgentRun(alertId) {
  return request(`/alerts/${encodeURIComponent(alertId)}/agent-run`, { method: "POST" });
}

export function getFollowUpQueries(alertId) {
  return request(`/alerts/${encodeURIComponent(alertId)}/follow-up-queries`);
}

export function getDecisionsSummary() {
  return request("/decisions/summary");
}

export function postDecision(payload) {
  return request("/decisions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postSaiaExplain(payload) {
  return request("/saia/explain", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postSaiaGenerate(payload) {
  return request("/saia/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function postAlertChat(alertId, payload) {
  return request(`/alerts/${encodeURIComponent(alertId)}/chat`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export { baseUrl };

import { useState } from "react";
import {
  getApiBaseUrl,
  getStoredApiBaseUrl,
  setStoredApiBaseUrl,
  usesMisconfiguredApi,
} from "../apiConfig.js";

export default function HostedApiBanner() {
  const show = usesMisconfiguredApi();
  const [draft, setDraft] = useState(() => getStoredApiBaseUrl() || "");
  const [error, setError] = useState(null);

  if (!show) return null;

  function handleSave(e) {
    e.preventDefault();
    setError(null);
    const value = draft.trim();
    if (!value) {
      setError("Enter the full API base URL (for example http://192.168.1.10:8001).");
      return;
    }
    try {
      const parsed = new URL(value);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        throw new Error("URL must start with http:// or https://");
      }
      setStoredApiBaseUrl(parsed.origin);
      window.location.reload();
    } catch {
      setError("Enter a valid URL (for example http://192.168.1.10:8001).");
    }
  }

  function handleClear() {
    setStoredApiBaseUrl("");
    window.location.reload();
  }

  const active = getApiBaseUrl();

  return (
    <div className="hosted-api-banner" role="status">
      <div className="hosted-api-banner__head">
        <strong className="hosted-api-banner__title">Backend connection required</strong>
        <span className="hosted-api-banner__badge">GitHub Pages UI only</span>
      </div>
      <p className="hosted-api-banner__text">
        This site hosts the TrustOps <strong>frontend</strong> only. Splunk and the FastAPI
        backend must run on a reachable host. From another device, point this UI at that host
        (not <code>localhost</code>).
      </p>
      {active && !usesMisconfiguredApi() ? (
        <p className="hosted-api-banner__active">
          Using API: <code>{active}</code>
        </p>
      ) : null}
      <form className="hosted-api-banner__form" onSubmit={handleSave}>
        <label className="hosted-api-banner__label" htmlFor="trustops-api-url">
          TrustOps API base URL
        </label>
        <div className="hosted-api-banner__row">
          <input
            id="trustops-api-url"
            className="hosted-api-banner__input"
            type="url"
            placeholder="http://192.168.1.10:8001"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            spellCheck={false}
          />
          <button type="submit" className="btn btn--primary btn--sm">
            Connect
          </button>
          {getStoredApiBaseUrl() ? (
            <button type="button" className="btn btn--ghost btn--sm" onClick={handleClear}>
              Clear
            </button>
          ) : null}
        </div>
      </form>
      {error ? <p className="hosted-api-banner__error">{error}</p> : null}
      <p className="hosted-api-banner__hint">
        Tip: share a one-time link with{" "}
        <code>?api=http://YOUR_SERVER:8001</code> — the URL is saved in this browser.
      </p>
    </div>
  );
}

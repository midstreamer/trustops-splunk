import { useEffect, useState } from "react";
import { getHealth } from "../api.js";

function mapSplunkLabel(health) {
  if (!health?.splunk_configured) return "Not configured";
  if (health.splunk_reachable === true) return "Reachable";
  return "Not reachable";
}

export default function StatusBar({ refreshKey = 0 }) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getHealth()
      .then((h) => {
        if (!cancelled) {
          setHealth(h);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setHealth(null);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const backendOnline = !error && health != null;
  const splunkLabel = health ? mapSplunkLabel(health) : error ? "Unknown" : "…";

  return (
    <div className="status-bar" role="status">
      <div className="status-bar__item">
        <span
          className={`status-dot ${backendOnline ? "status-dot--ok" : "status-dot--bad"}`}
          aria-hidden
        />
        <span className="status-bar__label">Backend</span>
        <strong>{loading ? "Checking…" : backendOnline ? "Online" : "Offline"}</strong>
      </div>
      <div className="status-bar__item">
        <span
          className={`status-dot ${
            health?.splunk_reachable
              ? "status-dot--ok"
              : health?.splunk_configured
                ? "status-dot--bad"
                : "status-dot--warn"
          }`}
          aria-hidden
        />
        <span className="status-bar__label">Splunk</span>
        <strong>{loading ? "Checking…" : splunkLabel}</strong>
      </div>
      {health?.detail && !error ? (
        <p className="status-bar__detail">{health.detail}</p>
      ) : null}
      {error ? <p className="status-bar__detail">{error}</p> : null}
    </div>
  );
}

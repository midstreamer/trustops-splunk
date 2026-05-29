import { useCallback, useEffect, useState } from "react";
import { getDecisionsSummary } from "../api.js";

function statusPillClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "accepted") return "status-pill status-pill--accepted";
  if (s === "modified") return "status-pill status-pill--modified";
  if (s === "rejected") return "status-pill status-pill--rejected";
  return "status-pill";
}

function fmtNum(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const x = Number(n);
  return Number.isInteger(x) ? String(x) : x.toFixed(2);
}

export default function MetricsPanel({ refreshKey = 0 }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getDecisionsSummary()
      .then((data) => {
        setRows(Array.isArray(data?.rows) ? data.rows : []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e.message);
        setRows([]);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <div className="panel app-grid__metrics">
      <div className="panel__header">
        <span>Decision metrics</span>
        <button type="button" className="btn btn--ghost" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      <div className="panel__body">
        {loading ? <div className="loading">Loading metrics…</div> : null}
        {error ? <div className="error-banner">{error}</div> : null}
        {!loading && !error && rows.length === 0 ? (
          <div className="empty-state">No decision telemetry yet.</div>
        ) : null}
        {!loading && !error && rows.length > 0 ? (
          <div className="data-table-wrap">
            <table className="metrics-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Count</th>
                  <th>Avg conf.</th>
                  <th>Avg trust</th>
                  <th>Avg TTD (s)</th>
                  <th>Avg bias risk</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.ai_recommendation_status}-${i}`}>
                    <td>
                      <span className={statusPillClass(r.ai_recommendation_status)}>
                        {r.ai_recommendation_status}
                      </span>
                    </td>
                    <td>{r.decision_count}</td>
                    <td>{fmtNum(r.avg_confidence)}</td>
                    <td>{fmtNum(r.avg_trust)}</td>
                    <td>{fmtNum(r.avg_time_to_decision)}</td>
                    <td>{fmtNum(r.avg_automation_bias_risk_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}

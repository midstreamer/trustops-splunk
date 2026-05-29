const CANONICAL_ID = "TO-VPN-2026-514";

function severityBadgeClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "high" || s === "critical") return "badge badge--high";
  if (s === "medium") return "badge badge--medium";
  return "badge badge--low";
}

function formatSrcIp(alert) {
  const ips = alert.related_src_ips;
  if (!ips?.length) return "—";
  if (ips.length === 1) return ips[0];
  return `${ips[0]} +${ips.length - 1}`;
}

export default function AlertQueue({ alerts, loading, error, selectedId, onSelect }) {
  if (loading) {
    return (
      <div className="panel">
        <div className="panel__header">Alert queue</div>
        <div className="panel__body">
          <div className="loading">Loading alerts…</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel">
        <div className="panel__header">Alert queue</div>
        <div className="panel__body">
          <div className="error-banner">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel app-grid__queue">
      <div className="panel__header">Alert queue</div>
      <div className="panel__body panel__body--flush">
        <div className="alert-list">
          {alerts.map((a) => {
            const canonical = a.alert_id === CANONICAL_ID;
            const selected = a.alert_id === selectedId;
            return (
              <button
                key={a.alert_id}
                type="button"
                className={`alert-card ${selected ? "alert-card--selected" : ""} ${canonical ? "alert-card--canonical" : ""}`}
                onClick={() => onSelect(a.alert_id)}
              >
                <div className="alert-card__id">{a.alert_id}</div>
                <div className="alert-card__title">{a.title}</div>
                <div className="badge-row">
                  <span className={severityBadgeClass(a.severity)}>{a.severity}</span>
                  {canonical ? <span className="badge badge--demo">Demo</span> : null}
                </div>
                <div className="alert-card__meta">
                  <span>
                    <strong>User:</strong> {a.user}
                  </span>
                  <span>
                    <strong>Src IP:</strong> {formatSrcIp(a)}
                  </span>
                  <span>
                    <strong>Scenario:</strong> {a.scenario}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export { CANONICAL_ID };

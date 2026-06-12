import AgentInvestigationSections from "./AgentInvestigationSections.jsx";
import AlertChatPanel from "./AlertChatPanel.jsx";

function severityBadgeClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "high" || s === "critical") return "badge badge--high";
  if (s === "medium") return "badge badge--medium";
  return "badge badge--low";
}

function trustCalibrationLevelClass(level) {
  const s = String(level || "").toLowerCase();
  if (s === "high") return "badge badge--calibration-high";
  if (s === "moderate") return "badge badge--calibration-moderate";
  return "badge badge--calibration-low";
}

function investigationSourceBadgeClass(source) {
  return source === "saia" ? "badge badge--saia" : "badge badge--fallback";
}

function investigationSourceLabel(source) {
  return source === "saia" ? "Splunk AI Assistant" : "TrustOps local fallback";
}

export default function InvestigationPanel({
  investigation,
  loading,
  error,
  agentPlan,
  onFollowUpQueriesViewed,
  onContradictoryViewed,
  onAgentPlanViewed,
}) {
  if (loading) {
    return (
      <div className="panel panel--investigation">
        <div className="panel__header">Investigation</div>
        <div className="panel__body">
          <div className="loading">Asking Splunk AI Assistant for investigation guidance…</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel panel--investigation">
        <div className="panel__header">Investigation</div>
        <div className="panel__body">
          <div className="error-banner">{error}</div>
        </div>
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="panel panel--investigation">
        <div className="panel__header">Investigation</div>
        <div className="panel__body">
          <p className="empty-state">Select an alert from the queue.</p>
        </div>
      </div>
    );
  }

  const calLevel = investigation.trust_calibration_level || "low";
  const invSource = investigation.investigation_source || "fallback";

  return (
    <div className="panel panel--investigation">
      <div className="panel__header">
        <span>Investigation</span>
        <span className="badge badge--low" style={{ fontWeight: 600 }}>
          {investigation.alert?.alert_id}
        </span>
      </div>

      <div className="panel__body panel__body--investigation">
        <div className="investigation-stack">
          <div className="investigation-ai-head">
            <span className="investigation-ai-head__title">Agentic investigation</span>
            {agentPlan?.run ? (
              <span className="badge badge--agent-complete">{agentPlan.run.status}</span>
            ) : agentPlan?.loading ? (
              <span className="badge badge--agent-running">running</span>
            ) : (
              <span className="badge badge--agent-pending">not run</span>
            )}
          </div>

          <div className="investigation-ai-head">
            <span className="investigation-ai-head__title">Splunk AI analysis</span>
            <span className={investigationSourceBadgeClass(invSource)}>
              {investigationSourceLabel(invSource)}
            </span>
          </div>
          {investigation.investigation_source_detail && invSource === "fallback" ? (
            <p className="investigation-ai-note" role="note">
              {investigation.investigation_source_detail}
            </p>
          ) : null}

          <p className="investigation-summary">
            <strong>Summary</strong> — {investigation.investigation_summary}
          </p>

          <div className="callout callout--compact">
            <div className="callout__label">Key evidence</div>
            <ul className="evidence-list evidence-list--compact">
              {(investigation.key_evidence || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="callout callout--compact">
            <div className="callout__label">Severity, actions, and confidence</div>
            <p className="investigation-meta">
              <strong>Recommended severity</strong>{" "}
              <span className={severityBadgeClass(investigation.recommended_severity)}>
                {investigation.recommended_severity}
              </span>
            </p>
            <p className="investigation-meta">
              <strong>Recommended actions</strong>
            </p>
            <ul className="evidence-list evidence-list--compact">
              {(investigation.recommended_actions || []).map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
            <p className="investigation-meta investigation-meta--last">
              <strong>Confidence rationale</strong> — {investigation.confidence_rationale}
            </p>
          </div>

          <div className="callout callout--compact callout--ai">
            <div className="callout__label">AI recommendation</div>
            <p className="callout__text">{investigation.ai_recommendation}</p>
            {investigation.trust_calibration_notice ? (
              <div className="trust-calibration-strip" role="note">
                <div className="trust-calibration-strip__head">
                  <span className="trust-calibration-strip__title">Trust Calibration</span>
                  <span className={trustCalibrationLevelClass(calLevel)}>
                    {calLevel.charAt(0).toUpperCase() + calLevel.slice(1)}
                  </span>
                </div>
                <p className="trust-calibration-strip__text">
                  {investigation.trust_calibration_notice}
                </p>
              </div>
            ) : null}
          </div>

          <AlertChatPanel
            alertId={investigation.alert?.alert_id}
            investigation={investigation}
          />

          <AgentInvestigationSections
            investigation={investigation}
            agentPlan={agentPlan}
            onFollowUpQueriesViewed={onFollowUpQueriesViewed}
            onContradictoryViewed={onContradictoryViewed}
            onAgentPlanViewed={onAgentPlanViewed}
          />
        </div>
      </div>
    </div>
  );
}

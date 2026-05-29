import { useCallback, useEffect, useState } from "react";
import { postSaiaExplain, postSaiaGenerate } from "../api.js";
import AgentPlanPanel from "./AgentPlanPanel.jsx";
import AlertChatPanel from "./AlertChatPanel.jsx";
import FollowUpQueriesPanel from "./FollowUpQueriesPanel.jsx";
import MitreAttackMappingPanel from "./MitreAttackMappingPanel.jsx";
import SplExplanationPanel from "./SplExplanationPanel.jsx";

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

function splunkSearchUrl(spl) {
  const q = encodeURIComponent(spl.trim());
  return `http://localhost:8000/en-US/app/search/search?q=${q}`;
}

function defaultGeneratePrompt(investigation) {
  const user = investigation?.alert?.user || "jsmith";
  const alertId = investigation?.alert?.alert_id || "";
  return (
    `Show VPN authentication events for user ${user} in index trustops, ` +
    `including failed logins and any successful login from an unusual country` +
    (alertId ? ` related to alert ${alertId}` : "")
  );
}

export default function InvestigationPanel({
  investigation,
  loading,
  error,
  onAgentPlanViewed,
  onFollowUpQueriesViewed,
}) {
  const [saiaLoading, setSaiaLoading] = useState(null);
  const [saiaError, setSaiaError] = useState(null);
  const [explainResult, setExplainResult] = useState(null);
  const [generateResult, setGenerateResult] = useState(null);
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [showGeneratePrompt, setShowGeneratePrompt] = useState(false);

  useEffect(() => {
    setExplainResult(null);
    setGenerateResult(null);
    setSaiaError(null);
    setSaiaLoading(null);
    setShowGeneratePrompt(false);
    if (investigation) {
      setGeneratePrompt(defaultGeneratePrompt(investigation));
    }
  }, [investigation?.alert?.alert_id]);

  const handleExplain = useCallback(async () => {
    const spl = investigation?.spl_query_used?.trim();
    if (!spl) return;
    setSaiaLoading("explain");
    setSaiaError(null);
    try {
      const data = await postSaiaExplain({
        spl,
        additional_context: investigation?.alert?.summary || undefined,
      });
      setExplainResult(data);
      setGenerateResult(null);
    } catch (e) {
      setSaiaError(e.message);
      setExplainResult(null);
    } finally {
      setSaiaLoading(null);
    }
  }, [investigation]);

  const handleGenerate = useCallback(async () => {
    const prompt = generatePrompt.trim();
    if (!prompt) return;
    setSaiaLoading("generate");
    setSaiaError(null);
    try {
      const data = await postSaiaGenerate({
        prompt,
        alert_id: investigation?.alert?.alert_id,
        spl_only: false,
        additional_context: investigation?.investigation_summary || undefined,
      });
      setGenerateResult(data);
      setExplainResult(null);
    } catch (e) {
      setSaiaError(e.message);
      setGenerateResult(null);
    } finally {
      setSaiaLoading(null);
    }
  }, [investigation, generatePrompt]);

  if (loading) {
    return (
      <div className="panel panel--investigation">
        <div className="panel__header">Investigation</div>
        <div className="panel__body">
          <div className="loading">Loading investigation…</div>
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

  const ev = investigation.events || [];
  const splBusy = saiaLoading === "explain";
  const genBusy = saiaLoading === "generate";
  const calLevel = investigation.trust_calibration_level || "low";

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
          <p className="investigation-summary">
            <strong>Summary</strong> — {investigation.investigation_summary}
          </p>

          <AgentPlanPanel
            alertId={investigation.alert?.alert_id}
            onViewed={onAgentPlanViewed}
          />

          <MitreAttackMappingPanel
            mappings={investigation.mitre_attack_mappings}
            rationale={investigation.mitre_attack_rationale}
          />

          <div className="callout callout--compact">
            <div className="callout__label">Key evidence</div>
            <ul className="evidence-list evidence-list--compact">
              {(investigation.key_evidence || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
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

          <details className="investigation-details">
            <summary className="investigation-details__summary">
              Severity, actions, and confidence
            </summary>
            <div className="investigation-details__body">
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
          </details>

          <FollowUpQueriesPanel
            investigation={investigation}
            onViewed={onFollowUpQueriesViewed}
            additionalContext={investigation.investigation_summary}
          />

          <AlertChatPanel
            alertId={investigation.alert?.alert_id}
            investigation={investigation}
          />

          <div className="investigation-spl-block">
            <div className="spl-toolbar">
              <p className="spl-toolbar__title">
                <strong>SPL query used</strong>
              </p>
              <div className="spl-toolbar__actions">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={handleExplain}
                  disabled={!investigation.spl_query_used || splBusy || genBusy}
                >
                  {splBusy ? "Explaining…" : "Explain SPL"}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setShowGeneratePrompt((v) => !v)}
                  disabled={splBusy || genBusy}
                >
                  {showGeneratePrompt ? "Hide prompt" : "Generate SPL"}
                </button>
                {investigation.spl_query_used ? (
                  <a
                    className="btn btn--ghost btn--sm"
                    href={splunkSearchUrl(investigation.spl_query_used)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open in Splunk AI
                  </a>
                ) : null}
              </div>
            </div>
            <pre className="spl-block spl-block--primary">
              {investigation.spl_query_used || "—"}
            </pre>

            {showGeneratePrompt ? (
              <div className="saia-prompt saia-prompt--compact">
                <label className="saia-prompt__label" htmlFor="saia-generate-prompt">
                  Natural language prompt
                </label>
                <textarea
                  id="saia-generate-prompt"
                  className="saia-prompt__input"
                  rows={2}
                  value={generatePrompt}
                  onChange={(e) => setGeneratePrompt(e.target.value)}
                  disabled={genBusy}
                />
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={handleGenerate}
                  disabled={!generatePrompt.trim() || genBusy || splBusy}
                >
                  {genBusy ? "Generating…" : "Run generate"}
                </button>
              </div>
            ) : null}

            {saiaError ? (
              <div className="error-banner saia-result saia-result--compact">{saiaError}</div>
            ) : null}

            {explainResult ? (
              <SplExplanationPanel
                spl={investigation.spl_query_used}
                investigation={investigation}
                rawText={explainResult.text}
                source={explainResult.source}
                onClose={() => setExplainResult(null)}
              />
            ) : null}

            {generateResult ? (
              <div className="callout saia-result saia-result--compact">
                <div className="callout__label saia-result__header">
                  <span>Generated SPL</span>
                  <span
                    className={`badge ${generateResult.source === "saia" ? "badge--saia" : "badge--fallback"}`}
                  >
                    {generateResult.source === "saia" ? "Splunk AI Assistant" : "Local fallback"}
                  </span>
                </div>
                {generateResult.generated_spl ? (
                  <pre className="spl-block spl-block--generated">
                    {generateResult.generated_spl}
                  </pre>
                ) : null}
                {generateResult.text && !generateResult.generated_spl ? (
                  <div className="saia-result__text">{generateResult.text}</div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="investigation-timeline">
        <div className="investigation-timeline__header">
          <strong>Related event timeline</strong>
          <span className="investigation-timeline__count">{ev.length} rows</span>
        </div>
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>_time</th>
                <th>user</th>
                <th>src_ip</th>
                <th>geo_country</th>
                <th>action</th>
                <th>auth_method</th>
                <th>risk_score</th>
              </tr>
            </thead>
            <tbody>
              {ev.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">
                    No events returned from Splunk for this alert.
                  </td>
                </tr>
              ) : (
                ev.map((row, i) => (
                  <tr key={i}>
                    <td>{row._time ?? "—"}</td>
                    <td>{row.user ?? "—"}</td>
                    <td>{row.src_ip ?? "—"}</td>
                    <td>{row.geo_country ?? "—"}</td>
                    <td>{row.action ?? "—"}</td>
                    <td>{row.auth_method ?? "—"}</td>
                    <td>{row.risk_score ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

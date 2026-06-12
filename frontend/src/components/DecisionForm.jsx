import { useCallback, useEffect, useMemo, useState } from "react";
import { postDecision } from "../api.js";

const EVIDENCE_CHECK_ITEMS = [
  { id: "auth_timeline", label: "Reviewed authentication timeline" },
  { id: "source_ip_history", label: "Reviewed source IP history" },
  { id: "geo_anomaly", label: "Reviewed geography anomaly" },
  { id: "benign_explanation", label: "Considered benign explanation" },
  { id: "sop_comparison", label: "Compared recommendation to SOP" },
];

const defaultForm = () => ({
  analyst: "demo_analyst",
  analyst_decision: "Escalate to incident response",
  final_severity: "High",
  ai_recommendation: "",
  confidence_score: 4,
  trust_score: 4,
  ai_recommendation_status: "accepted",
  evidence_reviewed_count: 0,
  sop_followed: true,
  notes: "",
  supporting_evidence: "",
  contradicting_evidence: "",
});

const defaultChecks = () =>
  Object.fromEntries(EVIDENCE_CHECK_ITEMS.map((c) => [c.id, false]));

function newClientDecisionId() {
  return crypto.randomUUID();
}

function elapsedSeconds(selectionStartedAtMs) {
  return Math.max(
    0,
    Math.floor((Date.now() - (selectionStartedAtMs || Date.now())) / 1000)
  );
}

function buildFormFromInvestigation(investigation) {
  return {
    analyst: "demo_analyst",
    analyst_decision: "Escalate to incident response",
    final_severity: investigation?.recommended_severity || "High",
    ai_recommendation: investigation?.ai_recommendation || "",
    confidence_score: 4,
    trust_score: 4,
    ai_recommendation_status: "accepted",
    evidence_reviewed_count: 0,
    sop_followed: true,
    notes: "",
    supporting_evidence: "",
    contradicting_evidence: "",
  };
}

function biasBadgeClass(level) {
  const s = String(level || "").toLowerCase();
  if (s === "high") return "badge badge--bias-high";
  if (s === "moderate") return "badge badge--bias-moderate";
  return "badge badge--bias-low";
}

function buildEvidenceChecklist(checked) {
  return EVIDENCE_CHECK_ITEMS.filter((c) => checked[c.id])
    .map((c) => c.id)
    .join("|");
}

function submitButtonLabel({ hasSubmitted, isSubmitting, readyToSubmit }) {
  if (hasSubmitted) return "Decision submitted to Splunk";
  if (isSubmitting) return "Submitting...";
  if (!readyToSubmit) return "Complete required fields";
  return "Submit decision to Splunk";
}

export default function DecisionForm({
  alertId,
  investigation,
  agenticViews = {},
  onSubmitted,
  disabled,
}) {
  const [form, setForm] = useState(defaultForm);
  const [evidenceChecks, setEvidenceChecks] = useState(defaultChecks);
  const [clientDecisionId, setClientDecisionId] = useState(() => newClientDecisionId());
  const [decisionStartedAtMs, setDecisionStartedAtMs] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submissionResult, setSubmissionResult] = useState(null);
  const [validation, setValidation] = useState({});

  const formLocked = disabled || isSubmitting || hasSubmitted;

  const checkedCount = useMemo(
    () => EVIDENCE_CHECK_ITEMS.filter((c) => evidenceChecks[c.id]).length,
    [evidenceChecks]
  );

  const readyToSubmit = useMemo(
    () =>
      checkedCount >= 2 &&
      Boolean(form.supporting_evidence.trim()) &&
      Boolean(form.contradicting_evidence.trim()) &&
      Boolean(form.analyst_decision.trim()),
    [
      checkedCount,
      form.supporting_evidence,
      form.contradicting_evidence,
      form.analyst_decision,
    ]
  );

  const resetSubmissionState = useCallback(() => {
    setHasSubmitted(false);
    setSubmissionResult(null);
    setSubmitError(null);
    setIsSubmitting(false);
    setValidation({});
  }, []);

  const loadDefaultsForAlert = useCallback(() => {
    if (!investigation || !alertId) {
      setForm(defaultForm());
      setEvidenceChecks(defaultChecks());
      return;
    }
    setForm(buildFormFromInvestigation(investigation));
    setEvidenceChecks(defaultChecks());
  }, [investigation, alertId]);

  useEffect(() => {
    resetSubmissionState();
    setClientDecisionId(newClientDecisionId());
    loadDefaultsForAlert();
    if (investigation && alertId) {
      setDecisionStartedAtMs(Date.now());
    } else {
      setDecisionStartedAtMs(null);
    }
  }, [investigation, alertId, resetSubmissionState, loadDefaultsForAlert]);

  useEffect(() => {
    setForm((f) => ({ ...f, evidence_reviewed_count: checkedCount }));
  }, [checkedCount]);

  function updateField(name, value) {
    setForm((f) => ({ ...f, [name]: value }));
  }

  function toggleCheck(id) {
    setEvidenceChecks((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function validate() {
    const errs = {};
    if (checkedCount < 2) {
      errs.evidence = "Select at least two evidence checks before submitting your decision.";
    }
    if (!form.supporting_evidence.trim()) {
      errs.supporting_evidence = "Supporting evidence is required.";
    }
    if (!form.contradicting_evidence.trim()) {
      errs.contradicting_evidence = "Contradicting evidence is required.";
    }
    if (!form.analyst_decision.trim()) {
      errs.analyst_decision = "Analyst decision is required.";
    }
    setValidation(errs);
    return Object.keys(errs).length === 0;
  }

  function handleStartNewDecision() {
    resetSubmissionState();
    setClientDecisionId(newClientDecisionId());
    setDecisionStartedAtMs(Date.now());
    loadDefaultsForAlert();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!alertId || !investigation) return;
    if (isSubmitting || hasSubmitted) return;
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmissionResult(null);
    try {
      const elapsed = elapsedSeconds(decisionStartedAtMs);
      const data = await postDecision({
        client_decision_id: clientDecisionId,
        alert_id: alertId,
        analyst: form.analyst.trim(),
        ai_recommendation: form.ai_recommendation.trim(),
        analyst_decision: form.analyst_decision.trim(),
        final_severity: form.final_severity.trim(),
        confidence_score: Number(form.confidence_score),
        trust_score: Number(form.trust_score),
        time_to_decision_seconds: elapsed,
        ai_recommendation_status: form.ai_recommendation_status,
        evidence_reviewed_count: checkedCount,
        sop_followed: Boolean(form.sop_followed),
        notes: form.notes.trim(),
        evidence_checklist: buildEvidenceChecklist(evidenceChecks),
        supporting_evidence: form.supporting_evidence.trim(),
        contradicting_evidence: form.contradicting_evidence.trim(),
        agent_plan_viewed: Boolean(agenticViews.agent_plan_viewed),
        follow_up_queries_viewed: Boolean(agenticViews.follow_up_queries_viewed),
        contradictory_evidence_viewed: Boolean(agenticViews.contradictory_evidence_viewed),
      });
      setSubmissionResult(data);
      setHasSubmitted(true);
      onSubmitted?.();
    } catch (err) {
      setSubmitError(err.message || "Submit failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!alertId || !investigation) {
    return (
      <div className="panel panel--decision">
        <div className="panel__header">Analyst decision</div>
        <div className="panel__body">
          <p className="empty-state">Select an alert and wait for the investigation to load.</p>
        </div>
      </div>
    );
  }

  const buttonLabel = submitButtonLabel({ hasSubmitted, isSubmitting, readyToSubmit });

  return (
    <div className="panel panel--decision">
      <div className="panel__header">Analyst decision</div>
      <div className="panel__body panel__body--decision">
        {hasSubmitted ? (
          <div className="decision-submitted-banner" role="status">
            <strong className="decision-submitted-banner__title">Decision Submitted</strong>
            <p className="decision-submitted-banner__text">
              This decision has been logged to Splunk. To submit another decision for this alert,
              select Start new decision.
            </p>
          </div>
        ) : null}

        {submitError ? <div className="error-banner decision-error">{submitError}</div> : null}

        <form onSubmit={handleSubmit} className="decision-form">
          <section className="form-section form-section--card">
            <h3 className="form-section__title">Decision Details</h3>
            <div className="form-grid form-grid--compact">
              <div className="form-field">
                <label htmlFor="analyst">Analyst</label>
                <input
                  id="analyst"
                  value={form.analyst}
                  onChange={(e) => updateField("analyst", e.target.value)}
                  disabled={formLocked}
                />
              </div>
              <div className="form-field">
                <label htmlFor="final_severity">Final severity</label>
                <select
                  id="final_severity"
                  value={form.final_severity}
                  onChange={(e) => updateField("final_severity", e.target.value)}
                  disabled={formLocked}
                >
                  <option>High</option>
                  <option>Medium</option>
                  <option>Low</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="confidence_score">Confidence (1–5)</label>
                <input
                  id="confidence_score"
                  type="number"
                  min={1}
                  max={5}
                  value={form.confidence_score}
                  onChange={(e) => updateField("confidence_score", e.target.value)}
                  disabled={formLocked}
                />
              </div>
              <div className="form-field">
                <label htmlFor="trust_score">Trust (1–5)</label>
                <input
                  id="trust_score"
                  type="number"
                  min={1}
                  max={5}
                  value={form.trust_score}
                  onChange={(e) => updateField("trust_score", e.target.value)}
                  disabled={formLocked}
                />
              </div>
              <div className="form-field">
                <label htmlFor="ai_recommendation_status">AI status</label>
                <select
                  id="ai_recommendation_status"
                  value={form.ai_recommendation_status}
                  onChange={(e) => updateField("ai_recommendation_status", e.target.value)}
                  disabled={formLocked}
                >
                  <option value="accepted">accepted</option>
                  <option value="modified">modified</option>
                  <option value="rejected">rejected</option>
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="sop_followed">SOP followed</label>
                <select
                  id="sop_followed"
                  value={form.sop_followed ? "yes" : "no"}
                  onChange={(e) => updateField("sop_followed", e.target.value === "yes")}
                  disabled={formLocked}
                >
                  <option value="yes">true</option>
                  <option value="no">false</option>
                </select>
              </div>
              <div className="form-field form-field--wide">
                <label htmlFor="ai_recommendation">AI recommendation</label>
                <textarea
                  id="ai_recommendation"
                  rows={2}
                  value={form.ai_recommendation}
                  onChange={(e) => updateField("ai_recommendation", e.target.value)}
                  disabled={formLocked}
                />
              </div>
              <div className="form-field form-field--wide">
                <label htmlFor="analyst_decision">Analyst decision</label>
                <textarea
                  id="analyst_decision"
                  rows={2}
                  value={form.analyst_decision}
                  onChange={(e) => updateField("analyst_decision", e.target.value)}
                  disabled={formLocked}
                />
                {validation.analyst_decision ? (
                  <p className="form-validation">{validation.analyst_decision}</p>
                ) : null}
              </div>
              <div className="form-field form-field--wide">
                <label htmlFor="notes">Notes (optional)</label>
                <textarea
                  id="notes"
                  rows={2}
                  value={form.notes}
                  onChange={(e) => updateField("notes", e.target.value)}
                  disabled={formLocked}
                />
              </div>
            </div>
          </section>

          <section className="form-section form-section--card">
            <h3 className="form-section__title">Evidence Review Checklist</h3>
            <p className="form-hint">Select at least two checks (count updates automatically).</p>
            <ul className="checklist checklist--grid">
              {EVIDENCE_CHECK_ITEMS.map((item) => (
                <li key={item.id}>
                  <label className="checklist__label">
                    <input
                      type="checkbox"
                      checked={!!evidenceChecks[item.id]}
                      onChange={() => toggleCheck(item.id)}
                      disabled={formLocked}
                    />
                    <span>{item.label}</span>
                  </label>
                </li>
              ))}
            </ul>
            {validation.evidence ? (
              <p className="form-validation">{validation.evidence}</p>
            ) : null}
            <div className="form-field form-field--inline-count">
              <label htmlFor="evidence_reviewed_count">Evidence reviewed count</label>
              <input
                id="evidence_reviewed_count"
                type="number"
                min={0}
                max={5}
                value={form.evidence_reviewed_count}
                readOnly
                title="Updated automatically from checklist selections"
              />
            </div>
          </section>

          <section className="form-section form-section--card">
            <h3 className="form-section__title">Challenge the AI Recommendation</h3>
            <div className="form-field form-field--wide">
              <label htmlFor="supporting_evidence">
                What evidence supports the AI recommendation?
              </label>
              <textarea
                id="supporting_evidence"
                rows={2}
                placeholder="Example: Seven failed VPN/SAML attempts followed by a successful login from Romania."
                value={form.supporting_evidence}
                onChange={(e) => updateField("supporting_evidence", e.target.value)}
                disabled={formLocked}
              />
              {validation.supporting_evidence ? (
                <p className="form-validation">{validation.supporting_evidence}</p>
              ) : null}
            </div>
            <div className="form-field form-field--wide">
              <label htmlFor="contradicting_evidence">
                What evidence could challenge or weaken the AI recommendation?
              </label>
              <textarea
                id="contradicting_evidence"
                rows={2}
                placeholder="Example: User may be traveling, vendor activity may be approved, or IP enrichment may be incomplete."
                value={form.contradicting_evidence}
                onChange={(e) => updateField("contradicting_evidence", e.target.value)}
                disabled={formLocked}
              />
              {validation.contradicting_evidence ? (
                <p className="form-validation">{validation.contradicting_evidence}</p>
              ) : null}
            </div>
          </section>

          <section className="form-section form-section--card form-section--submit">
            <h3 className="form-section__title">Submit and Feedback</h3>

            {!hasSubmitted ? (
              <div
                className={`submit-readiness ${readyToSubmit ? "submit-readiness--ready" : "submit-readiness--pending"}`}
                role="status"
              >
                {readyToSubmit ? (
                  <span className="submit-readiness__text submit-readiness__text--ready">
                    Ready to submit
                  </span>
                ) : (
                  <span className="submit-readiness__text">
                    Complete evidence review and AI challenge fields before submitting.
                  </span>
                )}
              </div>
            ) : null}

            <div className="form-actions">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={formLocked || !readyToSubmit || isSubmitting || hasSubmitted}
              >
                {buttonLabel}
              </button>
              {hasSubmitted ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={handleStartNewDecision}
                >
                  Start new decision
                </button>
              ) : null}
            </div>

            {submissionResult ? (
              <div className="post-decision-feedback" aria-live="polite">
                <p className="post-decision-feedback__success">Decision logged to Splunk.</p>
                {submissionResult.decision?.time_to_decision_seconds != null ? (
                  <p className="post-decision-feedback__timing">
                    Time to decision: {submissionResult.decision.time_to_decision_seconds}s
                    (recorded automatically)
                  </p>
                ) : null}
                <div className="post-decision-feedback__row">
                  <span className="post-decision-feedback__label">Automation Bias Risk</span>
                  <span
                    className={biasBadgeClass(submissionResult.automation_bias_risk_level)}
                  >
                    {submissionResult.automation_bias_risk_level}
                  </span>
                  <span className="post-decision-feedback__score">
                    Score: {submissionResult.automation_bias_risk_score}
                  </span>
                </div>
                <p className="post-decision-feedback__message">
                  {submissionResult.feedback_message}
                </p>
                <p className="post-decision-feedback__learning">
                  <strong>Learning point</strong> — {submissionResult.learning_point}
                </p>
              </div>
            ) : null}
          </section>
        </form>
      </div>
    </div>
  );
}

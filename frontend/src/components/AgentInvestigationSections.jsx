import { useCallback, useEffect, useState } from "react";
import { postSaiaExplain } from "../api.js";
import AgentResultSection from "./AgentResultSection.jsx";
import { MitreMappingCard } from "./MitreAttackMappingPanel.jsx";
import SplExplanationPanel from "./SplExplanationPanel.jsx";

function stepByName(steps, name) {
  return (steps || []).find((s) => s.agent_name === name);
}

function severityBadgeClass(sev) {
  const s = String(sev || "").toLowerCase();
  if (s === "high" || s === "critical") return "badge badge--high";
  if (s === "medium") return "badge badge--medium";
  return "badge badge--low";
}

function priorityBadgeClass(priority) {
  const p = String(priority || "").toLowerCase();
  if (p === "high") return "badge badge--high";
  if (p === "medium") return "badge badge--medium";
  return "badge badge--low";
}

function ContradictoryContent({ data }) {
  if (!data) return null;
  const has =
    data.possible_benign_explanations?.length ||
    data.recommended_validation_steps?.length ||
    data.evidence_gaps?.length;
  if (!has) return null;

  return (
    <div className="agent-section__challenge-grid">
      {data.possible_benign_explanations?.length ? (
        <div className="agent-section__challenge-col">
          <p className="investigation-meta">
            <strong>Possible benign explanations</strong>
          </p>
          <ul className="evidence-list evidence-list--compact">
            {data.possible_benign_explanations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {data.recommended_validation_steps?.length ? (
        <div className="agent-section__challenge-col">
          <p className="investigation-meta">
            <strong>Recommended validation steps</strong>
          </p>
          <ul className="evidence-list evidence-list--compact">
            {data.recommended_validation_steps.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {data.evidence_gaps?.length ? (
        <div className="agent-section__challenge-col">
          <p className="investigation-meta">
            <strong>Evidence gaps</strong>
          </p>
          <ul className="evidence-list evidence-list--compact">
            {data.evidence_gaps.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function FollowUpQueriesContent({ investigation, onViewed }) {
  const queries = investigation?.follow_up_queries || [];
  const [expandedSpl, setExpandedSpl] = useState({});
  const [copyOk, setCopyOk] = useState(null);
  const [explainState, setExplainState] = useState(null);
  const [explainLoading, setExplainLoading] = useState(null);
  const [explainError, setExplainError] = useState(null);

  useEffect(() => {
    setExpandedSpl({});
    setExplainState(null);
    setExplainError(null);
    setExplainLoading(null);
  }, [investigation?.alert?.alert_id]);

  useEffect(() => {
    if (queries.length) onViewed?.();
  }, [queries.length, onViewed]);

  const handleExplain = useCallback(
    async (query) => {
      const spl = query.spl?.trim();
      if (!spl) return;
      setExplainLoading(query.title);
      setExplainError(null);
      try {
        const data = await postSaiaExplain({
          spl,
          additional_context: investigation?.investigation_summary || query.purpose,
        });
        setExplainState({ query, data });
      } catch (e) {
        setExplainError(e.message);
        setExplainState(null);
      } finally {
        setExplainLoading(null);
      }
    },
    [investigation]
  );

  async function handleCopy(spl, title) {
    try {
      await navigator.clipboard.writeText(spl);
      setCopyOk(title);
      setTimeout(() => setCopyOk(null), 2000);
    } catch {
      setCopyOk(null);
    }
  }

  if (!queries.length) return null;

  return (
    <div className="agent-section__follow-ups">
      <p className="investigation-meta">
        <strong>Follow-up SPL queries</strong>
      </p>
      {explainError ? <div className="error-banner agent-section__inline-error">{explainError}</div> : null}
      {queries.map((q) => (
        <div key={q.title} className="follow-up-card follow-up-card--compact">
          <div className="follow-up-card__head">
            <span className="follow-up-card__title">{q.title}</span>
            <span className={priorityBadgeClass(q.priority)}>{q.priority}</span>
          </div>
          <p className="follow-up-card__purpose">{q.purpose}</p>
          <div className="follow-up-card__actions">
            <button
              type="button"
              className="btn btn--ghost btn--xs"
              onClick={() => setExpandedSpl((prev) => ({ ...prev, [q.title]: !prev[q.title] }))}
            >
              {expandedSpl[q.title] ? "Hide SPL" : "Show SPL"}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--xs"
              onClick={() => handleCopy(q.spl, q.title)}
            >
              {copyOk === q.title ? "Copied" : "Copy SPL"}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--xs"
              onClick={() => handleExplain(q)}
              disabled={explainLoading === q.title}
            >
              {explainLoading === q.title ? "Explaining…" : "Explain SPL"}
            </button>
          </div>
          {expandedSpl[q.title] ? (
            <pre className="spl-block spl-block--follow-up">{q.spl}</pre>
          ) : null}
        </div>
      ))}
      {explainState ? (
        <SplExplanationPanel
          spl={explainState.query.spl}
          investigation={investigation}
          rawText={explainState.data.text}
          source={explainState.data.source}
          onClose={() => setExplainState(null)}
        />
      ) : null}
    </div>
  );
}

export default function AgentInvestigationSections({
  investigation,
  agentPlan,
  onFollowUpQueriesViewed,
  onContradictoryViewed,
  onAgentPlanViewed,
}) {
  const run = agentPlan?.run;
  const steps = run?.steps || [];
  const hasRun = !!run;

  const contradictory = investigation?.contradictory_evidence;
  const hasContradictory =
    contradictory &&
    ((contradictory.possible_benign_explanations?.length || 0) > 0 ||
      (contradictory.recommended_validation_steps?.length || 0) > 0 ||
      (contradictory.evidence_gaps?.length || 0) > 0);

  useEffect(() => {
    if (hasRun) onAgentPlanViewed?.();
  }, [hasRun, run?.run_id, onAgentPlanViewed]);

  useEffect(() => {
    if (hasContradictory) onContradictoryViewed?.();
  }, [hasContradictory, onContradictoryViewed]);

  const evidenceStep = stepByName(steps, "Evidence Agent");
  const triageStep = stepByName(steps, "Triage Agent");
  const splStep = stepByName(steps, "SPL Agent");
  const mitreStep = stepByName(steps, "MITRE ATT&CK Mapping Agent");
  const challengeStep = stepByName(steps, "Contradictory Evidence Agent");
  const sopStep = stepByName(steps, "SOP Agent");
  const trustStep = stepByName(steps, "Trust Calibration Agent");

  const mitreMappings =
    mitreStep?.mitre_mappings?.length
      ? mitreStep.mitre_mappings
      : investigation?.mitre_attack_mappings;

  return (
    <div className="agent-sections">
      {agentPlan?.error ? (
        <div className="error-banner agent-sections__error">{agentPlan.error}</div>
      ) : null}

      {agentPlan?.loading ? (
        <p className="callout__text callout__text--muted">Running agentic investigation…</p>
      ) : null}

      <AgentResultSection
        label="Evidence Agent"
        step={evidenceStep}
        pending={!hasRun && !agentPlan?.loading}
        summary={
          !evidenceStep && !hasRun ? investigation?.investigation_summary : undefined
        }
        evidence={
          !evidenceStep && !hasRun ? investigation?.key_evidence : undefined
        }
      />

      <AgentResultSection
        label="Triage Agent"
        step={triageStep}
        pending={!hasRun && !agentPlan?.loading}
        summary={
          !triageStep && !hasRun
            ? `Recommended severity: ${investigation?.recommended_severity || "—"}. ${investigation?.confidence_rationale || ""}`
            : undefined
        }
      >
        {!triageStep && !hasRun && investigation?.recommended_severity ? (
          <p className="investigation-meta">
            <strong>Recommended severity</strong>{" "}
            <span className={severityBadgeClass(investigation.recommended_severity)}>
              {investigation.recommended_severity}
            </span>
          </p>
        ) : null}
      </AgentResultSection>

      <AgentResultSection label="SPL Agent" step={splStep} pending={!hasRun && !agentPlan?.loading}>
        <FollowUpQueriesContent
          investigation={investigation}
          onViewed={onFollowUpQueriesViewed}
        />
      </AgentResultSection>

      <AgentResultSection
        label="MITRE ATT&CK Mapping Agent"
        step={mitreStep}
        pending={!hasRun && !agentPlan?.loading && !mitreMappings?.length}
        summary={
          !mitreStep && investigation?.mitre_attack_rationale
            ? investigation.mitre_attack_rationale
            : undefined
        }
      >
        {mitreMappings?.length ? (
          <div className="agent-section__mitre-grid">
            {mitreMappings.map((m) => (
              <MitreMappingCard key={m.technique_id} mapping={m} />
            ))}
          </div>
        ) : null}
      </AgentResultSection>

      <AgentResultSection
        label="Contradictory Evidence Agent"
        step={challengeStep}
        pending={!hasRun && !agentPlan?.loading && !hasContradictory}
      >
        {!challengeStep && hasContradictory ? (
          <ContradictoryContent data={contradictory} />
        ) : null}
      </AgentResultSection>

      <AgentResultSection
        label="SOP Agent"
        step={sopStep}
        pending={!hasRun && !agentPlan?.loading}
        recommendations={
          !sopStep && !hasRun ? investigation?.recommended_actions : undefined
        }
      />

      <AgentResultSection
        label="Trust Calibration Agent"
        step={trustStep}
        pending={!hasRun && !agentPlan?.loading}
        summary={
          !trustStep && !hasRun ? investigation?.trust_calibration_notice : undefined
        }
      />
    </div>
  );
}

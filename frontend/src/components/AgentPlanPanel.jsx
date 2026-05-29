import { useCallback, useEffect, useMemo, useState } from "react";
import { postAgentRun } from "../api.js";
import { MitreAgentMappingsTable } from "./MitreAttackMappingPanel.jsx";

const TIMELINE_ORDER = [
  "Evidence Agent",
  "Triage Agent",
  "SPL Agent",
  "MITRE ATT&CK Mapping Agent",
  "Contradictory Evidence Agent",
  "SOP Agent",
  "Trust Calibration Agent",
];

const AGENT_META = {
  "Evidence Agent": { category: "Evidence", timeline: "Evidence", defaultOpen: true },
  "Triage Agent": { category: "Severity", timeline: "Triage", defaultOpen: true },
  "SPL Agent": { category: "Query", timeline: "SPL", defaultOpen: true },
  "MITRE ATT&CK Mapping Agent": {
    category: "ATT&CK",
    timeline: "ATT&CK",
    defaultOpen: true,
    badge: "ATT&CK",
  },
  "Contradictory Evidence Agent": { category: "Challenge", timeline: "Challenge", defaultOpen: false },
  "SOP Agent": { category: "Response", timeline: "SOP", defaultOpen: false },
  "Trust Calibration Agent": { category: "Oversight", timeline: "Trust", defaultOpen: false },
};

function statusBadgeClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "complete") return "badge badge--agent-complete";
  if (s === "running") return "badge badge--agent-running";
  if (s === "error") return "badge badge--agent-error";
  return "badge badge--agent-pending";
}

function formatTs(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts;
  }
}

function runWorkflowStats(run) {
  const steps = run?.steps || [];
  let totalMs = 0;
  const tools = new Set();
  let errors = 0;

  for (const s of steps) {
    if (s.status === "error") errors += 1;
    if (s.started_at && s.completed_at) {
      try {
        totalMs += Math.max(0, new Date(s.completed_at) - new Date(s.started_at));
      } catch {
        /* ignore */
      }
    }
    (s.tools_used || []).forEach((t) => tools.add(t));
  }

  let splunkEvents = 0;
  let failures = 0;
  let successes = 0;
  let mitreTechniques = 0;
  const mitreStep = steps.find((s) => s.agent_name === "MITRE ATT&CK Mapping Agent");
  if (mitreStep?.mitre_techniques?.length) {
    mitreTechniques = mitreStep.mitre_techniques.length;
  } else if (mitreStep?.mitre_mappings?.length) {
    mitreTechniques = mitreStep.mitre_mappings.length;
  }
  const evidenceStep = steps.find((s) => s.agent_name === "Evidence Agent");
  for (const line of evidenceStep?.evidence || []) {
    const evMatch = line.match(/Retrieved (\d+)/i);
    const failMatch = line.match(/Failures:\s*(\d+)/i);
    const succMatch = line.match(/successes:\s*(\d+)/i);
    if (evMatch) splunkEvents = parseInt(evMatch[1], 10);
    if (failMatch) failures = parseInt(failMatch[1], 10);
    if (succMatch) successes = parseInt(succMatch[1], 10);
  }

  return {
    stepCount: steps.length,
    errors,
    splunkEvents,
    failures,
    successes,
    mitreTechniques,
    tools: [...tools],
    totalMs,
    durationLabel:
      totalMs >= 1000 ? `${Math.round(totalMs / 1000)}s` : totalMs > 0 ? `${totalMs}ms` : "—",
  };
}

function sortSteps(steps) {
  const order = new Map(TIMELINE_ORDER.map((n, i) => [n, i]));
  return [...(steps || [])].sort(
    (a, b) => (order.get(a.agent_name) ?? 99) - (order.get(b.agent_name) ?? 99)
  );
}

function buildCopyText(step) {
  const parts = [
    step.agent_name,
    step.output_summary || "",
    ...(step.evidence || []),
    ...(step.recommendations || []),
  ].filter(Boolean);
  return parts.join("\n");
}

function AgentTimeline({ steps }) {
  const ordered = sortSteps(steps);
  return (
    <div className="agent-timeline" aria-label="Workflow step timeline">
      <p className="agent-timeline__heading">Investigation flow</p>
      <div className="agent-timeline__track">
        {ordered.map((step, i) => {
          const meta = AGENT_META[step.agent_name] || { timeline: "?" };
          const isError = step.status === "error";
          return (
            <div key={step.agent_name} className="agent-timeline__segment-wrap">
              {i > 0 ? <span className="agent-timeline__connector" aria-hidden="true" /> : null}
              <div className="agent-timeline__segment">
                <div
                  className={`agent-timeline__node ${isError ? "agent-timeline__node--error" : "agent-timeline__node--complete"}`}
                  title={`${step.agent_name}: ${step.status}`}
                >
                  <span className="agent-timeline__step-num">{i + 1}</span>
                  <span className="agent-timeline__label">{meta.timeline}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgentStepCard({ step, expanded, onToggle, onCopy, copyOk }) {
  const meta = AGENT_META[step.agent_name] || { category: "Step", defaultOpen: false };
  const showInput =
    step.input_summary &&
    step.input_summary.trim() !== step.objective?.trim();

  return (
    <article
      className={`agent-card ${step.status === "error" ? "agent-card--error" : ""} ${expanded ? "agent-card--open" : "agent-card--closed"}`}
    >
      <div className="agent-card__top">
        <div className="agent-card__head">
          <div className="agent-card__title-row">
            <span className="agent-card__category">{meta.category}</span>
            {meta.badge ? (
              <span className="agent-card__attack-badge">{meta.badge}</span>
            ) : null}
            <span className="agent-card__name">{step.agent_name}</span>
          </div>
          <span className={statusBadgeClass(step.status)}>{step.status}</span>
        </div>
        <p className="agent-card__role">{step.objective}</p>
        <p className="agent-card__result">{step.output_summary}</p>
        {step.tools_used?.length ? (
          <div className="agent-card__tools">
            {step.tools_used.map((t) => (
              <span key={t} className="agent-tool-badge">
                {t}
              </span>
            ))}
          </div>
        ) : null}
        <div className="agent-card__actions">
          <button type="button" className="btn btn--ghost btn--xs" onClick={onToggle}>
            {expanded ? "Less detail" : "More detail"}
          </button>
          <button type="button" className="btn btn--ghost btn--xs" onClick={onCopy}>
            {copyOk ? "Copied" : "Copy summary"}
          </button>
        </div>
      </div>

      {expanded ? (
        <div className="agent-card__details">
          {showInput ? (
            <div className="agent-card__detail-block">
              <span className="agent-card__detail-label">Input</span>
              <p className="agent-card__detail-text">{step.input_summary}</p>
            </div>
          ) : null}
          {step.agent_name === "MITRE ATT&CK Mapping Agent" && step.mitre_mappings?.length ? (
            <MitreAgentMappingsTable mappings={step.mitre_mappings} />
          ) : null}
          {step.evidence?.length ? (
            <div className="agent-card__detail-block">
              <span className="agent-card__detail-label">Evidence</span>
              <ul className="agent-card__list">
                {step.evidence.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {step.recommendations?.length ? (
            <div className="agent-card__detail-block">
              <span className="agent-card__detail-label">Recommendations</span>
              <ul className="agent-card__list agent-card__list--rec">
                {step.recommendations.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {step.error ? <p className="agent-card__error-text">{step.error}</p> : null}
          <p className="agent-card__times">
            {formatTs(step.started_at)} → {formatTs(step.completed_at)}
          </p>
        </div>
      ) : null}
    </article>
  );
}

export default function AgentPlanPanel({ alertId, onViewed }) {
  const [visible, setVisible] = useState(false);
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [copyKey, setCopyKey] = useState(null);

  const sortedSteps = useMemo(() => sortSteps(run?.steps), [run?.steps]);
  const stats = useMemo(() => (run ? runWorkflowStats(run) : null), [run]);

  const initExpanded = useCallback((steps) => {
    const next = {};
    for (const s of steps || []) {
      const meta = AGENT_META[s.agent_name];
      next[s.agent_name] = meta?.defaultOpen ?? false;
    }
    return next;
  }, []);

  useEffect(() => {
    setVisible(false);
    setRun(null);
    setError(null);
    setLoading(false);
    setExpanded({});
    setCopyKey(null);
  }, [alertId]);

  useEffect(() => {
    if (run?.steps?.length) {
      setExpanded(initExpanded(run.steps));
    }
  }, [run?.run_id, run?.steps, initExpanded]);

  useEffect(() => {
    if (visible && run) onViewed?.();
  }, [visible, run, onViewed]);

  async function handleRun() {
    if (!alertId) return;
    setLoading(true);
    setError(null);
    setVisible(true);
    try {
      const data = await postAgentRun(alertId);
      setRun(data);
    } catch (e) {
      setError(e.message);
      setRun(null);
    } finally {
      setLoading(false);
    }
  }

  function expandAll() {
    const next = {};
    sortedSteps.forEach((s) => {
      next[s.agent_name] = true;
    });
    setExpanded(next);
  }

  function collapseAll() {
    const next = {};
    sortedSteps.forEach((s) => {
      next[s.agent_name] = false;
    });
    setExpanded(next);
  }

  async function handleCopyStep(step) {
    try {
      await navigator.clipboard.writeText(buildCopyText(step));
      setCopyKey(step.agent_name);
      setTimeout(() => setCopyKey(null), 2000);
    } catch {
      setCopyKey(null);
    }
  }

  if (!alertId) return null;

  return (
    <div className="agent-plan">
      <p className="agent-plan__intro">
        Tool-backed <strong>agentic workflow</strong> with specialized roles. Each step records
        an execution trace (Splunk search, rules, SPL, SAIA when available)—not fully autonomous
        agents.
      </p>
      <div className="agent-plan__toolbar">
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={handleRun}
          disabled={loading}
        >
          {loading ? "Running agentic investigation…" : "Run agentic investigation"}
        </button>
        {run ? (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setVisible((v) => !v)}
          >
            {visible ? "Hide execution trace" : "Show execution trace"}
          </button>
        ) : null}
      </div>
      {error ? <div className="error-banner agent-plan__error">{error}</div> : null}
      {visible && run ? (
        <div className="agent-plan__body">
          <h3 className="agent-plan__title">Agentic investigation workflow</h3>
          <p className="agent-plan__subtitle">
            Seven specialized agent roles run sequentially. Each tool-backed step records tools
            used, evidence, recommendations, and timing.
          </p>
          <p className="agent-plan__transparency">
            Evidence Agent is grounded in live Splunk search results. SPL Agent uses Splunk AI
            Assistant when available.
          </p>

          <div className="agent-run-meta">
            <span>
              Run <code className="agent-run-meta__code">{run.run_id?.slice(0, 8)}…</code>
            </span>
            <span className={statusBadgeClass(run.status)}>{run.status}</span>
          </div>

          {stats ? (
            <div className="agent-stats-row">
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.stepCount}</span>
                <span className="agent-stat__label">Steps</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.errors}</span>
                <span className="agent-stat__label">Errors</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.splunkEvents}</span>
                <span className="agent-stat__label">Splunk events</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.failures}</span>
                <span className="agent-stat__label">Failures</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.successes}</span>
                <span className="agent-stat__label">Successes</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.mitreTechniques}</span>
                <span className="agent-stat__label">MITRE techniques</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.tools.length}</span>
                <span className="agent-stat__label">Tools used</span>
              </div>
              <div className="agent-stat">
                <span className="agent-stat__value">{stats.durationLabel}</span>
                <span className="agent-stat__label">Duration</span>
              </div>
            </div>
          ) : null}

          <AgentTimeline steps={run.steps} />

          {run.final_summary ? (
            <div className="agent-result-callout">
              <div className="agent-result-callout__title">Agentic Investigation Result</div>
              <p className="agent-result-callout__text">{run.final_summary}</p>
            </div>
          ) : null}

          <p className="agent-plan__summary agent-plan__summary--muted">{run.plan_summary}</p>

          {run.telemetry_logged ? (
            <p className="agent-telemetry-note agent-telemetry-note--ok">
              Agent run telemetry logged to Splunk ({run.telemetry_steps_logged} step
              {run.telemetry_steps_logged === 1 ? "" : "s"}).
            </p>
          ) : run.telemetry_warning ? (
            <p className="agent-telemetry-note agent-telemetry-note--warn">
              {run.telemetry_warning}
            </p>
          ) : null}

          {stats?.tools.length ? (
            <div className="agent-tools-panel">
              <span className="agent-tools-panel__label">Tools across workflow</span>
              <div className="agent-tools-panel__badges">
                {stats.tools.map((t) => (
                  <span key={t} className="agent-tool-badge">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="agent-plan__card-toolbar">
            <button type="button" className="btn btn--ghost btn--xs" onClick={expandAll}>
              Expand all
            </button>
            <button type="button" className="btn btn--ghost btn--xs" onClick={collapseAll}>
              Collapse all
            </button>
          </div>

          <div className="agent-plan__grid">
            {sortedSteps.map((step) => (
              <AgentStepCard
                key={`${step.agent_name}-${step.started_at}`}
                step={step}
                expanded={!!expanded[step.agent_name]}
                onToggle={() =>
                  setExpanded((prev) => ({
                    ...prev,
                    [step.agent_name]: !prev[step.agent_name],
                  }))
                }
                onCopy={() => handleCopyStep(step)}
                copyOk={copyKey === step.agent_name}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

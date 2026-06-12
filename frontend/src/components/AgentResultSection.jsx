function statusBadgeClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "complete") return "badge badge--agent-complete";
  if (s === "running") return "badge badge--agent-running";
  if (s === "error") return "badge badge--agent-error";
  return "badge badge--agent-pending";
}

function AgentTools({ tools }) {
  if (!tools?.length) return null;
  return (
    <div className="agent-section__tools">
      {tools.map((t) => (
        <span key={t} className="agent-tool-badge">
          {t}
        </span>
      ))}
    </div>
  );
}

function AgentBulletBlock({ title, items }) {
  if (!items?.length) return null;
  return (
    <div className="agent-section__column">
      <p className="investigation-meta">
        <strong>{title}</strong>
      </p>
      <ul className="evidence-list evidence-list--compact">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AgentResultSection({
  label,
  step,
  pending = false,
  summary,
  evidence,
  recommendations,
  tools,
  children,
}) {
  const hasContent =
    summary ||
    step?.output_summary ||
    evidence?.length ||
    step?.evidence?.length ||
    recommendations?.length ||
    step?.recommendations?.length ||
    children;

  if (!hasContent && !pending) return null;

  const outputText = summary || step?.output_summary;
  const evidenceItems = evidence ?? step?.evidence ?? [];
  const recommendationItems = recommendations ?? step?.recommendations ?? [];
  const toolItems = tools ?? step?.tools_used ?? [];

  return (
    <div
      className={`callout callout--compact callout--ai agent-section ${
        step?.status === "error" ? "agent-section--error" : ""
      }`}
    >
      <div className="agent-section__head">
        <div className="callout__label">{label}</div>
        {step ? (
          <span className={statusBadgeClass(step.status)}>{step.status}</span>
        ) : pending ? (
          <span className="badge badge--agent-pending">awaiting run</span>
        ) : null}
      </div>

      {step?.objective ? <p className="agent-section__objective">{step.objective}</p> : null}

      {outputText ? <p className="callout__text">{outputText}</p> : null}

      {!outputText && pending ? (
        <p className="callout__text callout__text--muted">
          Run agentic investigation to populate this agent.
        </p>
      ) : null}

      {step?.error ? <p className="agent-section__error">{step.error}</p> : null}

      {evidenceItems.length || recommendationItems.length ? (
        <div className="agent-section__columns">
          <AgentBulletBlock title="Evidence" items={evidenceItems} />
          <AgentBulletBlock title="Recommendations" items={recommendationItems} />
        </div>
      ) : null}

      {children}

      <AgentTools tools={toolItems} />
    </div>
  );
}

export { statusBadgeClass };

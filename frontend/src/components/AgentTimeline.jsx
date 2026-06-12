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
  "Evidence Agent": { timeline: "Evidence" },
  "Triage Agent": { timeline: "Triage" },
  "SPL Agent": { timeline: "SPL" },
  "MITRE ATT&CK Mapping Agent": { timeline: "ATT&CK" },
  "Contradictory Evidence Agent": { timeline: "Challenge" },
  "SOP Agent": { timeline: "SOP" },
  "Trust Calibration Agent": { timeline: "Trust" },
};

export function sortSteps(steps) {
  const order = new Map(TIMELINE_ORDER.map((n, i) => [n, i]));
  return [...(steps || [])].sort(
    (a, b) => (order.get(a.agent_name) ?? 99) - (order.get(b.agent_name) ?? 99)
  );
}

export function buildPlaceholderTimelineSteps(status = "running") {
  return TIMELINE_ORDER.map((agent_name) => ({ agent_name, status }));
}

export default function AgentTimeline({
  steps,
  compact = false,
  showHeading = true,
  heading = "Investigation flow",
}) {
  const ordered = sortSteps(steps);
  return (
    <div
      className={`agent-timeline ${compact ? "agent-timeline--compact" : ""}`}
      aria-label="Workflow step timeline"
    >
      {showHeading ? <p className="agent-timeline__heading">{heading}</p> : null}
      <div className="agent-timeline__track">
        {ordered.map((step, i) => {
          const meta = AGENT_META[step.agent_name] || { timeline: "?" };
          const status = String(step.status || "").toLowerCase();
          const isError = status === "error";
          const isRunning = status === "running";
          const isComplete = status === "complete";
          const nodeClass = isError
            ? "agent-timeline__node--error"
            : isRunning
              ? "agent-timeline__node--running"
              : isComplete
                ? "agent-timeline__node--complete"
                : "agent-timeline__node--pending";
          return (
            <div key={`${step.agent_name}-${i}`} className="agent-timeline__segment-wrap">
              {i > 0 ? <span className="agent-timeline__connector" aria-hidden="true" /> : null}
              <div className="agent-timeline__segment">
                <div
                  className={`agent-timeline__node ${nodeClass}`}
                  title={`${step.agent_name}: ${step.status || "pending"}`}
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

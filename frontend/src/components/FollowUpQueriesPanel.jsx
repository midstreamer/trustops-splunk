import { useCallback, useEffect, useState } from "react";
import { postSaiaExplain } from "../api.js";
import SplExplanationPanel from "./SplExplanationPanel.jsx";

function priorityBadgeClass(priority) {
  const p = String(priority || "").toLowerCase();
  if (p === "high") return "badge badge--high";
  if (p === "medium") return "badge badge--medium";
  return "badge badge--low";
}

export default function FollowUpQueriesPanel({
  investigation,
  onViewed,
  additionalContext,
}) {
  const queries = investigation?.follow_up_queries || [];
  const [visible, setVisible] = useState(false);
  const [expandedSpl, setExpandedSpl] = useState({});
  const [copyOk, setCopyOk] = useState(null);
  const [explainState, setExplainState] = useState(null);
  const [explainLoading, setExplainLoading] = useState(null);
  const [explainError, setExplainError] = useState(null);

  useEffect(() => {
    setVisible(false);
    setExpandedSpl({});
    setExplainState(null);
    setExplainError(null);
    setExplainLoading(null);
  }, [investigation?.alert?.alert_id]);

  useEffect(() => {
    if (visible && queries.length > 0) onViewed?.();
  }, [visible, queries.length, onViewed]);

  const handleExplain = useCallback(
    async (query) => {
      const spl = query.spl?.trim();
      if (!spl) return;
      setExplainLoading(query.title);
      setExplainError(null);
      try {
        const data = await postSaiaExplain({
          spl,
          additional_context: additionalContext || query.purpose,
        });
        setExplainState({ query, data });
      } catch (e) {
        setExplainError(e.message);
        setExplainState(null);
      } finally {
        setExplainLoading(null);
      }
    },
    [additionalContext]
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
    <div className="follow-up-queries">
      <div className="follow-up-queries__toolbar">
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? "Hide recommended follow-ups" : "Show recommended follow-ups"}
        </button>
      </div>

      {visible ? (
        <div className="follow-up-queries__body">
          <h3 className="follow-up-queries__title">Recommended Follow-Up SPL</h3>
          <p className="follow-up-queries__hint">
            Suggested searches for deeper validation — copy or explain; queries are not executed
            from TrustOps.
          </p>
          {explainError ? (
            <div className="error-banner follow-up-queries__error">{explainError}</div>
          ) : null}
          <div className="follow-up-queries__list">
            {queries.map((q) => (
              <div key={q.title} className="follow-up-card">
                <div className="follow-up-card__head">
                  <span className="follow-up-card__title">{q.title}</span>
                  <span className={priorityBadgeClass(q.priority)}>{q.priority}</span>
                </div>
                <p className="follow-up-card__purpose">{q.purpose}</p>
                <div className="follow-up-card__actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() =>
                      setExpandedSpl((prev) => ({ ...prev, [q.title]: !prev[q.title] }))
                    }
                  >
                    {expandedSpl[q.title] ? "Hide SPL" : "Show SPL"}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => handleCopy(q.spl, q.title)}
                  >
                    {copyOk === q.title ? "Copied" : "Copy SPL"}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
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
          </div>
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
      ) : null}
    </div>
  );
}

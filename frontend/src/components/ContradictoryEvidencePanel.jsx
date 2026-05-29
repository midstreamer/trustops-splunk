import { useEffect } from "react";

export default function ContradictoryEvidencePanel({ contradictoryEvidence, onViewed }) {
  const data = contradictoryEvidence;
  const hasContent =
    data &&
    ((data.possible_benign_explanations?.length || 0) > 0 ||
      (data.recommended_validation_steps?.length || 0) > 0 ||
      (data.evidence_gaps?.length || 0) > 0);

  useEffect(() => {
    if (hasContent) onViewed?.();
  }, [hasContent, onViewed]);

  if (!hasContent) return null;

  return (
    <div className="panel panel--challenge">
      <div className="panel__header panel__header--compact">
        <span>Challenge the AI</span>
        <span className="badge badge--challenge">Contradictory Evidence Agent</span>
      </div>
      <div className="panel__body panel__body--compact">
        <p className="challenge-intro">
          Do not blindly accept the AI recommendation. Review benign hypotheses, validation steps,
          and evidence gaps before deciding.
        </p>
        <div className="challenge-grid">
          <section className="challenge-section">
            <h4 className="challenge-section__title">Possible benign explanations</h4>
            <ul className="challenge-list">
              {(data.possible_benign_explanations || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </section>
          <section className="challenge-section">
            <h4 className="challenge-section__title">Recommended validation steps</h4>
            <ul className="challenge-list">
              {(data.recommended_validation_steps || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </section>
          <section className="challenge-section challenge-section--gaps">
            <h4 className="challenge-section__title">Evidence gaps</h4>
            <ul className="challenge-list">
              {(data.evidence_gaps || []).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}

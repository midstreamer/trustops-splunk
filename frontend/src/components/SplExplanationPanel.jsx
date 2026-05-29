import { useMemo, useState } from "react";
import { formatSplExplanation } from "../utils/splExplanationFormatter.js";

function sourceBadgeClass(source) {
  return source === "saia" ? "badge badge--saia" : "badge badge--fallback";
}

export default function SplExplanationPanel({
  spl,
  investigation,
  rawText,
  source = "saia",
  onClose,
}) {
  const [splExpanded, setSplExpanded] = useState(false);
  const [rawExpanded, setRawExpanded] = useState(false);
  const [copyOk, setCopyOk] = useState(false);

  const model = useMemo(
    () => formatSplExplanation({ spl, investigation, rawText, source }),
    [spl, investigation, rawText, source]
  );

  async function handleCopySpl() {
    try {
      await navigator.clipboard.writeText(model.original_spl);
      setCopyOk(true);
      setTimeout(() => setCopyOk(false), 2000);
    } catch {
      setCopyOk(false);
    }
  }

  return (
    <div className="spl-explanation-panel">
      <div className="spl-explanation-panel__header">
        <div>
          <h3 className="spl-explanation-panel__title">SPL Explanation</h3>
          <p className="spl-explanation-panel__subtitle">
            AI-generated explanation formatted for analyst review
          </p>
        </div>
        <div className="spl-explanation-panel__header-actions">
          <span className={sourceBadgeClass(model.source)}>
            {model.source === "saia" ? "Splunk AI Assistant" : "Local fallback"}
          </span>
          {onClose ? (
            <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
              Close
            </button>
          ) : null}
        </div>
      </div>

      <div className="spl-explanation-panel__badges">
        {model.badges.map((b) => (
          <span key={b} className="spl-explanation-badge">
            {b}
          </span>
        ))}
      </div>

      <section className="spl-explanation-section">
        <h4 className="spl-explanation-section__title">Executive Summary</h4>
        <p className="spl-explanation-section__prose">{model.executive_summary}</p>
      </section>

      <section className="spl-explanation-section spl-explanation-card">
        <h4 className="spl-explanation-section__title">Query Purpose</h4>
        <ul className="spl-explanation-list">
          {model.query_purpose.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="spl-explanation-section">
        <h4 className="spl-explanation-section__title">Data Source</h4>
        <dl className="spl-explanation-kv">
          <div>
            <dt>Index</dt>
            <dd>{model.data_source.index}</dd>
          </div>
          <div>
            <dt>Sourcetype</dt>
            <dd>{model.data_source.sourcetype}</dd>
          </div>
          <div>
            <dt>Event type</dt>
            <dd>{model.data_source.event_type}</dd>
          </div>
          <div>
            <dt>Alert ID</dt>
            <dd>{model.data_source.alert_id}</dd>
          </div>
        </dl>
      </section>

      <section className="spl-explanation-section">
        <h4 className="spl-explanation-section__title">Query Steps</h4>
        <ol className="spl-explanation-steps">
          {model.query_steps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </section>

      <section className="spl-explanation-section">
        <h4 className="spl-explanation-section__title">Extracted Fields</h4>
        <div className="spl-explanation-fields-wrap">
          <table className="spl-explanation-fields">
            <thead>
              <tr>
                <th>Field</th>
                <th>Meaning</th>
              </tr>
            </thead>
            <tbody>
              {model.extracted_fields.map((row) => (
                <tr key={row.field}>
                  <td>
                    <code>{row.field}</code>
                  </td>
                  <td>{row.meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="spl-explanation-section spl-explanation-card spl-explanation-card--highlight">
        <h4 className="spl-explanation-section__title">Analyst Interpretation</h4>
        <ul className="spl-explanation-list">
          {model.analyst_interpretation.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="spl-explanation-section spl-explanation-card spl-explanation-card--warn">
        <h4 className="spl-explanation-section__title">Limitations / Analyst Checks</h4>
        <ul className="spl-explanation-list spl-explanation-list--compact">
          {model.limitations.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="spl-explanation-section">
        <div className="spl-explanation-spl-header">
          <h4 className="spl-explanation-section__title">Original SPL</h4>
          <div className="spl-explanation-spl-actions">
            <button type="button" className="btn btn--ghost btn--sm" onClick={handleCopySpl}>
              {copyOk ? "Copied" : "Copy SPL"}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setSplExpanded((v) => !v)}
            >
              {splExpanded ? "Collapse" : "Expand"}
            </button>
          </div>
        </div>
        {splExpanded ? (
          <pre className="spl-block spl-block--explanation">{model.original_spl}</pre>
        ) : (
          <pre className="spl-block spl-block--explanation spl-block--collapsed">
            {model.original_spl.split("\n").slice(0, 2).join("\n")}
            {model.original_spl.split("\n").length > 2 ? "\n…" : ""}
          </pre>
        )}
      </section>

      {model.raw_response ? (
        <details
          className="spl-explanation-raw"
          open={rawExpanded}
          onToggle={(e) => setRawExpanded(e.target.open)}
        >
          <summary className="spl-explanation-raw__summary">Raw AI Assistant Response</summary>
          <div className="spl-explanation-raw__body">{model.raw_response}</div>
        </details>
      ) : null}
    </div>
  );
}

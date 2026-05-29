import { useState } from "react";

function validationBadge(mapping) {
  if (mapping.validated) {
    return (
      <span className="mitre-badge mitre-badge--validated" title={mapping.enrichment_source}>
        Validated by MITRE ATT&CK data
      </span>
    );
  }
  return (
    <span className="mitre-badge mitre-badge--fallback" title={mapping.note || mapping.enrichment_source}>
      Local fallback mapping
    </span>
  );
}

function MitreMappingCard({ mapping }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const hasDetails =
    mapping.description ||
    mapping.detection ||
    (mapping.platforms && mapping.platforms.length) ||
    (mapping.data_sources && mapping.data_sources.length);

  return (
    <article className="mitre-mapping-card">
      <div className="mitre-mapping-card__head">
        <span className="mitre-chip">
          {mapping.technique_id} {mapping.technique}
        </span>
        {validationBadge(mapping)}
      </div>
      <p className="mitre-mapping-card__tactic">
        <strong>Tactic</strong> — {mapping.tactic}
      </p>
      <p className="mitre-mapping-card__rationale">{mapping.rationale}</p>
      {hasDetails ? (
        <details
          className="mitre-details"
          open={detailsOpen}
          onToggle={(e) => setDetailsOpen(e.target.open)}
        >
          <summary className="mitre-details__summary">ATT&CK details</summary>
          <div className="mitre-details__body">
            {mapping.description ? (
              <p className="mitre-details__text">{mapping.description}</p>
            ) : null}
            {mapping.detection ? (
              <p className="mitre-details__text">
                <strong>Detection</strong> — {mapping.detection}
              </p>
            ) : null}
            {mapping.platforms?.length ? (
              <p className="mitre-details__text">
                <strong>Platforms</strong> — {mapping.platforms.join(", ")}
              </p>
            ) : null}
            {mapping.data_sources?.length ? (
              <p className="mitre-details__text">
                <strong>Data sources</strong> — {mapping.data_sources.join(", ")}
              </p>
            ) : null}
            {mapping.url ? (
              <a
                className="mitre-details__link"
                href={mapping.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                MITRE technique reference
              </a>
            ) : null}
          </div>
        </details>
      ) : null}
    </article>
  );
}

export default function MitreAttackMappingPanel({ mappings, rationale }) {
  if (!mappings?.length) return null;

  return (
    <div className="mitre-panel callout callout--compact">
      <div className="mitre-panel__header">
        <h3 className="mitre-panel__title">MITRE ATT&CK Mapping</h3>
        <p className="mitre-panel__subtitle">
          Evidence mapped to enterprise ATT&CK tactics and techniques.
        </p>
      </div>
      {rationale ? <p className="mitre-panel__rationale">{rationale}</p> : null}
      <div className="mitre-panel__grid">
        {mappings.map((m) => (
          <MitreMappingCard key={m.technique_id} mapping={m} />
        ))}
      </div>
    </div>
  );
}

export function MitreAgentMappingsTable({ mappings }) {
  if (!mappings?.length) return null;

  return (
    <div className="mitre-agent-table-wrap">
      <span className="agent-card__detail-label">ATT&CK mappings</span>
      <table className="mitre-agent-table">
        <thead>
          <tr>
            <th>Tactic</th>
            <th>Technique</th>
            <th>ID</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((m) => (
            <tr key={m.technique_id}>
              <td>{m.tactic}</td>
              <td>
                <span className="mitre-chip mitre-chip--sm">
                  {m.technique_id} {m.technique}
                </span>
              </td>
              <td>{m.technique_id}</td>
              <td>{m.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mitre-agent-table__badges">
        {mappings.map((m) => (
          <span key={`v-${m.technique_id}`}>{validationBadge(m)}</span>
        ))}
      </div>
    </div>
  );
}

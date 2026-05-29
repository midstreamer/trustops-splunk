/**
 * Build a structured SPL explanation from the active SPL, investigation context,
 * and optional raw Splunk AI Assistant markdown.
 */

const EXTRACTED_FIELDS = [
  { field: "timestamp", meaning: "Original CSV timestamp string from _raw" },
  { field: "user", meaning: "Account associated with the authentication event" },
  { field: "src_ip", meaning: "Source IP address for the login attempt" },
  { field: "dest_host", meaning: "Destination host or VPN endpoint" },
  { field: "action", meaning: "Authentication outcome (success or failure)" },
  { field: "geo_country", meaning: "Geographic country inferred for the source" },
  { field: "auth_method", meaning: "Authentication method (e.g. vpn_saml)" },
  { field: "risk_score", meaning: "Numeric risk score from synthetic telemetry" },
  { field: "event_type", meaning: "Event classification in the demo dataset" },
  { field: "alert_id", meaning: "TrustOps alert identifier tying events to this case" },
  { field: "scenario", meaning: "Demo scenario label (e.g. vpn_brute_then_geo_anomaly)" },
];

function parseSplMeta(spl) {
  const lines = spl.split("\n").map((l) => l.trim()).filter(Boolean);
  const indexMatch = spl.match(/index\s*=\s*(\S+)/i);
  const stMatch = spl.match(/sourcetype\s*=\s*"([^"]+)"/i);
  const alertMatch = spl.match(/alert_id\s*=\s*"([^"]+)"/i);
  return {
    index: indexMatch?.[1] || "—",
    sourcetype: stMatch?.[1] || "—",
    alertId: alertMatch?.[1] || null,
    lines,
  };
}

function describeStage(line) {
  const lower = line.toLowerCase();
  if (lower.startsWith("search ")) {
    const idx = line.match(/index=(\S+)/i);
    const st = line.match(/sourcetype="([^"]+)"/i);
    let text = "Search authentication events";
    if (idx) text += ` in index \`${idx[1]}\``;
    if (st) text += ` with sourcetype \`${st[1]}\``;
    return text;
  }
  if (lower.includes("_is_header") || lower.includes("header")) {
    return "Flag or remove CSV header rows embedded in _raw";
  }
  if (lower.startsWith("| where") && lower.includes("_is_header")) {
    return "Drop synthetic CSV header rows from results";
  }
  if (lower.startsWith("| fields -")) {
    return "Remove helper fields used only during parsing";
  }
  if (lower.includes("rex field=_raw")) {
    return "Extract structured fields from comma-separated _raw CSV";
  }
  if (lower.includes("where alert_id")) {
    const m = line.match(/alert_id="([^"]+)"/i);
    return m
      ? `Keep only events for alert \`${m[1]}\``
      : "Filter events to the selected alert identifier";
  }
  if (lower.includes("strptime")) {
    return "Convert CSV timestamp into Splunk _time for timeline charts";
  }
  if (lower.startsWith("| sort")) {
    return "Sort events chronologically";
  }
  if (lower.startsWith("| table") || lower.startsWith("| head") || lower.startsWith("| tail")) {
    return "Project a concise table for analyst review";
  }
  return `Processing: \`${line.slice(0, 80)}${line.length > 80 ? "…" : ""}\``;
}

function buildQuerySteps(spl) {
  const { lines } = parseSplMeta(spl);
  const stages = [];
  for (const line of lines) {
    if (line.startsWith("|")) {
      stages.push(line.replace(/^\|\s*/, ""));
    } else if (line.toLowerCase().startsWith("search ")) {
      stages.push(line);
    }
  }
  return stages.map((s) => describeStage(s.startsWith("|") ? `| ${s}` : s));
}

function computeBadges(spl) {
  const lower = spl.toLowerCase();
  const badges = [];
  if (lower.includes("search ") || /index\s*=/.test(lower)) badges.push("Search");
  if (lower.includes("rex ") || lower.includes("extract")) badges.push("Field extraction");
  if (lower.includes("sort ") || lower.includes("table ") || lower.includes("strptime")) {
    badges.push("Timeline");
  }
  if (lower.includes("alert_id")) badges.push("Alert pivot");
  if (!/\bstats\b|\btimechart\b|\beventstats\b/.test(lower)) badges.push("No aggregation");
  return badges;
}

function buildAnalystInterpretation(investigation, events) {
  const bullets = [];
  const evidence = investigation?.key_evidence || [];
  for (const item of evidence.slice(0, 5)) {
    bullets.push(item);
  }

  const failures = events.filter((e) => String(e.action).toLowerCase() === "failure");
  const successes = events.filter((e) => String(e.action).toLowerCase() === "success");
  const users = [...new Set(events.map((e) => e.user).filter(Boolean))];
  const geos = [...new Set(events.map((e) => e.geo_country).filter(Boolean))];

  if (failures.length >= 3) {
    bullets.push(
      `${failures.length} failed VPN/SAML authentication attempts observed in the retrieved window.`
    );
  }
  if (users.length === 1) {
    bullets.push(`Activity is concentrated on user \`${users[0]}\`.`);
  }
  if (geos.length > 1) {
    bullets.push(`Multiple geographies seen: ${geos.join(", ")}.`);
  }
  if (successes.length && failures.length) {
    const successGeo = successes.map((e) => e.geo_country).filter(Boolean);
    bullets.push(
      `Successful login(s) follow failure burst` +
        (successGeo.length ? ` (including ${successGeo.join(", ")})` : "") +
        " — pattern may indicate credential testing followed by account takeover."
    );
  }

  if (!bullets.length && investigation?.investigation_summary) {
    bullets.push(investigation.investigation_summary);
  }

  return [...new Set(bullets)].slice(0, 6);
}

function buildExecutiveSummary(spl, alertId, steps, rawText) {
  const fromRaw = extractSummaryFromRaw(rawText);
  if (fromRaw) return fromRaw;

  const aid = alertId || "the selected alert";
  const index = parseSplMeta(spl).index;
  const parts = [
    `This SPL retrieves authentication events from index \`${index}\` for alert \`${aid}\`.`,
  ];
  if (steps.length >= 3) {
    parts.push(
      `It cleans CSV-shaped _raw data, extracts fields, filters to the alert, sorts chronologically, and presents a timeline for analyst review.`
    );
  } else {
    parts.push(
      "It shapes raw events into structured fields and a readable result set for triage."
    );
  }
  return parts.join(" ");
}

function extractSummaryFromRaw(raw) {
  if (!raw || raw.length < 40) return null;
  const cleaned = raw
    .replace(/\*\*/g, "")
    .replace(/^#+\s*/gm, "")
    .replace(/\|[^|\n]+\|/g, " ")
    .trim();
  const sentences = cleaned
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 20 && s.length < 320);
  if (sentences.length >= 2) {
    return sentences.slice(0, 3).join(" ");
  }
  if (sentences.length === 1) return sentences[0];
  return null;
}

function buildQueryPurpose(alertId, investigation) {
  const aid = alertId || investigation?.alert?.alert_id || "this alert";
  const user = investigation?.alert?.user;
  const purposes = [
    `Investigates alert \`${aid}\``,
    "Builds a chronological VPN authentication timeline",
    "Helps confirm whether failed VPN/SAML attempts were followed by a successful login from an unusual geography",
  ];
  if (user) {
    purposes.push(`Focuses on account activity for \`${user}\``);
  }
  return purposes.slice(0, 4);
}

function buildLimitations() {
  return [
    "The query depends on the Splunk time range selected in the UI or API.",
    "The rex parsing assumes comma-separated _raw fields in a consistent column order.",
    "Validate whether travel, vendor access, or approved remote activity explains any successful foreign login.",
  ];
}

/**
 * @param {{ spl: string, investigation?: object, rawText?: string, source?: string }} params
 */
export function formatSplExplanation({ spl, investigation, rawText = "", source = "saia" }) {
  const meta = parseSplMeta(spl);
  const alertId = meta.alertId || investigation?.alert?.alert_id || null;
  const events = investigation?.events || [];
  const steps = buildQuerySteps(spl);

  return {
    source,
    badges: computeBadges(spl),
    executive_summary: buildExecutiveSummary(spl, alertId, steps, rawText),
    query_purpose: buildQueryPurpose(alertId, investigation),
    data_source: {
      index: meta.index,
      sourcetype: meta.sourcetype,
      event_type: "Authentication logs",
      alert_id: alertId || "—",
    },
    query_steps: steps,
    extracted_fields: EXTRACTED_FIELDS,
    analyst_interpretation: buildAnalystInterpretation(investigation, events),
    limitations: buildLimitations(),
    original_spl: spl,
    raw_response: rawText || "",
  };
}

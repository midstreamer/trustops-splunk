/**
 * Lightweight formatter for Splunk AI Assistant chat answers (markdown subset).
 */

function parseTableRow(line) {
  const trimmed = line.trim();
  if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return null;
  const cells = trimmed
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim());
  return cells;
}

function isTableSeparator(line) {
  return /^\|[\s\-:|]+\|$/.test(line.trim());
}

function parseTable(lines) {
  const rows = [];
  for (const line of lines) {
    if (isTableSeparator(line)) continue;
    const cells = parseTableRow(line);
    if (cells) rows.push(cells);
  }
  if (rows.length < 2) return null;
  const [header, ...body] = rows;
  return { header, body };
}

function parseInline(text) {
  const parts = [];
  const re = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ type: "text", value: text.slice(last, m.index) });
    if (m[1] !== undefined) parts.push({ type: "strong", value: m[1] });
    else if (m[2] !== undefined) parts.push({ type: "em", value: m[2] });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ type: "text", value: text.slice(last) });
  return parts.length ? parts : [{ type: "text", value: text }];
}

function InlineText({ text }) {
  const parts = parseInline(text);
  return (
    <>
      {parts.map((p, i) => {
        if (p.type === "strong") return <strong key={i}>{p.value}</strong>;
        if (p.type === "em") return <em key={i}>{p.value}</em>;
        return <span key={i}>{p.value}</span>;
      })}
    </>
  );
}

function AnswerTable({ header, body }) {
  return (
    <div className="alert-chat__table-wrap">
      <table className="alert-chat__table">
        <thead>
          <tr>
            {header.map((cell, i) => (
              <th key={i}>
                <InlineText text={cell} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci}>
                  <InlineText text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function parseBlocks(text) {
  const raw = (text || "").trim();
  if (!raw) return [];

  const lines = raw.split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i += 1;
      }
      const table = parseTable(tableLines);
      if (table) blocks.push({ type: "table", ...table });
      else blocks.push({ type: "paragraph", text: tableLines.join("\n") });
      continue;
    }

    if (/^#{1,3}\s+/.test(trimmed)) {
      const level = trimmed.match(/^#+/)[0].length;
      blocks.push({
        type: "heading",
        level: Math.min(level, 3),
        text: trimmed.replace(/^#+\s+/, ""),
      });
      i += 1;
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith("|") &&
      !/^#{1,3}\s+/.test(lines[i].trim()) &&
      !/^[-*]\s+/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i].trim());
      i += 1;
    }
    if (paraLines.length) blocks.push({ type: "paragraph", text: paraLines.join(" ") });
  }

  return blocks;
}

export function answerIncludesSafetyNote(text, safetyNote) {
  if (!safetyNote || !text) return false;
  const a = text.toLowerCase();
  const s = safetyNote.toLowerCase();
  return a.includes(s.slice(0, 40));
}

export function ChatAnswerBody({ text }) {
  const blocks = parseBlocks(text);

  return (
    <div className="alert-chat__answer-body">
      {blocks.map((block, i) => {
        if (block.type === "table") {
          return <AnswerTable key={i} header={block.header} body={block.body} />;
        }
        if (block.type === "heading") {
          const Tag = block.level === 1 ? "h4" : block.level === 2 ? "h5" : "h6";
          return (
            <Tag key={i} className="alert-chat__heading">
              <InlineText text={block.text} />
            </Tag>
          );
        }
        if (block.type === "list") {
          return (
            <ul key={i} className="alert-chat__answer-list">
              {block.items.map((item, j) => (
                <li key={j}>
                  <InlineText text={item} />
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i} className="alert-chat__answer-p">
            <InlineText text={block.text} />
          </p>
        );
      })}
    </div>
  );
}

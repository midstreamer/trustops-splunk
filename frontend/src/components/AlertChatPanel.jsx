import { useCallback, useEffect, useMemo, useState } from "react";
import { postAlertChat } from "../api.js";
import { answerIncludesSafetyNote, ChatAnswerBody } from "../utils/chatAnswerFormatter.jsx";

const PROMPT_CHIPS = [
  "Why is this high severity?",
  "What evidence supports account takeover?",
  "What could make this benign?",
  "Generate follow-up SPL.",
  "Map this to MITRE ATT&CK.",
  "What should I do next according to the SOP?",
];

const MAX_EXCHANGES = 5;

function sourceBadgeClass(source) {
  return source === "splunk_ai_assistant"
    ? "badge badge--saia"
    : "badge badge--fallback";
}

function sourceLabel(source) {
  return source === "splunk_ai_assistant"
    ? "Splunk AI Assistant"
    : "TrustOps grounded answer";
}

export default function AlertChatPanel({ alertId, investigation }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [exchanges, setExchanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copyOk, setCopyOk] = useState(null);

  useEffect(() => {
    setOpen(false);
    setInput("");
    setConversationId(null);
    setExchanges([]);
    setError(null);
    setLoading(false);
    setCopyOk(null);
  }, [alertId]);

  const visibleExchanges = useMemo(
    () => exchanges.slice(-MAX_EXCHANGES),
    [exchanges]
  );

  const sendMessage = useCallback(
    async (text) => {
      const message = (text ?? input).trim();
      if (!message || !alertId || loading) return;

      setLoading(true);
      setError(null);
      setInput("");

      try {
        const data = await postAlertChat(alertId, {
          message,
          conversation_id: conversationId || undefined,
          include_context: true,
        });
        setConversationId(data.conversation_id);
        setExchanges((prev) => [
          ...prev,
          {
            question: message,
            answer: data.answer,
            evidence_used: data.evidence_used || [],
            suggested_spl: data.suggested_spl,
            source: data.source,
            safety_note: data.safety_note,
          },
        ]);
      } catch (e) {
        setError(e.message);
        setInput(message);
      } finally {
        setLoading(false);
      }
    },
    [alertId, conversationId, input, loading]
  );

  function handleClear() {
    setExchanges([]);
    setConversationId(null);
    setError(null);
    setInput("");
  }

  async function handleCopySpl(spl) {
    try {
      await navigator.clipboard.writeText(spl);
      setCopyOk(spl);
      setTimeout(() => setCopyOk(null), 2000);
    } catch {
      setCopyOk(null);
    }
  }

  if (!alertId) return null;

  return (
    <div className="alert-chat">
      <button
        type="button"
        className="alert-chat__toggle btn btn--ghost btn--sm"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? "Hide Ask Splunk AI" : "Ask Splunk AI about this alert"}
      </button>

      {open ? (
        <div className="alert-chat__panel">
          <p className="alert-chat__intro">
            Alert-scoped, read-only chat grounded in Splunk evidence for{" "}
            <strong>{investigation?.alert?.alert_id || alertId}</strong>. Not a generic chatbot.
          </p>

          <div className="alert-chat__chips">
            {PROMPT_CHIPS.map((chip) => (
              <button
                key={chip}
                type="button"
                className="alert-chat__chip"
                disabled={loading}
                onClick={() => sendMessage(chip)}
              >
                {chip}
              </button>
            ))}
          </div>

          {visibleExchanges.length ? (
            <div className="alert-chat__history">
              {visibleExchanges.map((ex, i) => (
                <div key={`${i}-${ex.question.slice(0, 24)}`} className="alert-chat__exchange">
                  <div className="alert-chat__bubble alert-chat__bubble--q">
                    <span className="alert-chat__role">You</span>
                    <p>{ex.question}</p>
                  </div>
                  <div className="alert-chat__bubble alert-chat__bubble--a">
                    <div className="alert-chat__answer-head">
                      <span className="alert-chat__role">Answer</span>
                      <span className={sourceBadgeClass(ex.source)}>{sourceLabel(ex.source)}</span>
                    </div>
                    <ChatAnswerBody text={ex.answer} />
                    {ex.evidence_used?.length ? (
                      <details className="alert-chat__evidence-details">
                        <summary className="alert-chat__evidence-label">
                          Evidence used ({ex.evidence_used.length})
                        </summary>
                        <ul className="alert-chat__evidence-list">
                          {ex.evidence_used.map((item, j) => (
                            <li key={j}>{item}</li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                    {ex.suggested_spl ? (
                      <div className="alert-chat__spl">
                        <div className="alert-chat__spl-head">
                          <span>Suggested SPL</span>
                          <button
                            type="button"
                            className="btn btn--ghost btn--xs"
                            onClick={() => handleCopySpl(ex.suggested_spl)}
                          >
                            {copyOk === ex.suggested_spl ? "Copied" : "Copy SPL"}
                          </button>
                        </div>
                        <pre className="alert-chat__spl-pre">{ex.suggested_spl}</pre>
                      </div>
                    ) : null}
                    {ex.safety_note && !answerIncludesSafetyNote(ex.answer, ex.safety_note) ? (
                      <p className="alert-chat__safety">{ex.safety_note}</p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="alert-chat__empty">Ask a follow-up question about this alert.</p>
          )}

          {error ? <div className="error-banner alert-chat__error">{error}</div> : null}

          <form
            className="alert-chat__form"
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
          >
            <input
              type="text"
              className="alert-chat__input"
              placeholder="Ask about severity, evidence, SPL, MITRE, SOP…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              maxLength={2000}
            />
            <button type="submit" className="btn btn--primary btn--sm" disabled={loading || !input.trim()}>
              {loading ? "Sending…" : "Send"}
            </button>
            {exchanges.length ? (
              <button type="button" className="btn btn--ghost btn--sm" onClick={handleClear} disabled={loading}>
                Clear chat
              </button>
            ) : null}
          </form>
        </div>
      ) : null}
    </div>
  );
}

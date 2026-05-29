import { useCallback, useEffect, useState } from "react";
import { CANONICAL_ID } from "./components/AlertQueue.jsx";
import AlertQueue from "./components/AlertQueue.jsx";
import DecisionForm from "./components/DecisionForm.jsx";
import ContradictoryEvidencePanel from "./components/ContradictoryEvidencePanel.jsx";
import InvestigationPanel from "./components/InvestigationPanel.jsx";
import MetricsPanel from "./components/MetricsPanel.jsx";
import StatusBar from "./components/StatusBar.jsx";
import { getAlerts, getInvestigation } from "./api.js";

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState(null);

  const [selectedAlertId, setSelectedAlertId] = useState(null);
  const [selectionStartedAtMs, setSelectionStartedAtMs] = useState(() => Date.now());

  const [investigation, setInvestigation] = useState(null);
  const [invLoading, setInvLoading] = useState(false);
  const [invError, setInvError] = useState(null);

  const [refreshKey, setRefreshKey] = useState(0);

  const [agenticViews, setAgenticViews] = useState({
    agent_plan_viewed: false,
    follow_up_queries_viewed: false,
    contradictory_evidence_viewed: false,
  });

  useEffect(() => {
    let cancelled = false;
    setAlertsLoading(true);
    setAlertsError(null);
    getAlerts()
      .then((data) => {
        if (cancelled) return;
        const list = Array.isArray(data) ? data : [];
        setAlerts(list);
        const preferred = list.find((a) => a.alert_id === CANONICAL_ID);
        const initial = preferred?.alert_id ?? list[0]?.alert_id ?? null;
        setSelectedAlertId(initial);
        setSelectionStartedAtMs(Date.now());
        setAlertsLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setAlertsError(e.message);
        setAlerts([]);
        setAlertsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setAgenticViews({
      agent_plan_viewed: false,
      follow_up_queries_viewed: false,
      contradictory_evidence_viewed: false,
    });
  }, [selectedAlertId]);

  useEffect(() => {
    if (!selectedAlertId) {
      setInvestigation(null);
      return;
    }
    let cancelled = false;
    setInvLoading(true);
    setInvError(null);
    setInvestigation(null);
    getInvestigation(selectedAlertId)
      .then((data) => {
        if (!cancelled) {
          setInvestigation(data);
          setInvLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setInvError(e.message);
          setInvestigation(null);
          setInvLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAlertId]);

  const handleSelectAlert = useCallback((id) => {
    setSelectedAlertId(id);
    setSelectionStartedAtMs(Date.now());
  }, []);

  const handleDecisionSubmitted = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>TrustOps for Splunk</h1>
        <p className="subtitle">Human-in-the-loop agentic triage for security operations</p>
      </header>

      <StatusBar refreshKey={refreshKey} />

      <div className="app-grid">
        <AlertQueue
          alerts={alerts}
          loading={alertsLoading}
          error={alertsError}
          selectedId={selectedAlertId}
          onSelect={handleSelectAlert}
        />

        <div className="app-grid__main">
          <InvestigationPanel
            investigation={investigation}
            loading={invLoading}
            error={invError}
            onAgentPlanViewed={() =>
              setAgenticViews((v) => ({ ...v, agent_plan_viewed: true }))
            }
            onFollowUpQueriesViewed={() =>
              setAgenticViews((v) => ({ ...v, follow_up_queries_viewed: true }))
            }
          />
          {investigation ? (
            <ContradictoryEvidencePanel
              contradictoryEvidence={investigation.contradictory_evidence}
              onViewed={() =>
                setAgenticViews((v) => ({ ...v, contradictory_evidence_viewed: true }))
              }
            />
          ) : null}
          <DecisionForm
            alertId={selectedAlertId}
            investigation={investigation}
            selectionStartedAtMs={selectionStartedAtMs}
            agenticViews={agenticViews}
            onSubmitted={handleDecisionSubmitted}
            disabled={invLoading || !!invError || !investigation}
          />
        </div>

        <MetricsPanel refreshKey={refreshKey} />
      </div>
    </div>
  );
}

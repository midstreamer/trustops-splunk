import { useCallback, useEffect, useState } from "react";
import { CANONICAL_ID } from "./components/AlertQueue.jsx";
import AlertQueue from "./components/AlertQueue.jsx";
import DecisionForm from "./components/DecisionForm.jsx";
import InvestigationPanel from "./components/InvestigationPanel.jsx";
import MetricsPanel from "./components/MetricsPanel.jsx";
import StatusBar from "./components/StatusBar.jsx";
import { useAgentPlanRun } from "./components/AgentPlanPanel.jsx";
import { getAlerts, getInvestigation } from "./api.js";

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [alertsError, setAlertsError] = useState(null);

  const [selectedAlertId, setSelectedAlertId] = useState(null);

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
  }, []);

  const handleDecisionSubmitted = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const handleAgentPlanViewed = useCallback(() => {
    setAgenticViews((v) => ({ ...v, agent_plan_viewed: true }));
  }, []);

  const agentPlan = useAgentPlanRun(selectedAlertId, handleAgentPlanViewed);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>TrustOps for Splunk</h1>
        <p className="subtitle">Human-in-the-loop agentic triage for security operations</p>
      </header>

      <StatusBar
        refreshKey={refreshKey}
        selectedAlertId={selectedAlertId}
        agentRunLoading={agentPlan.loading}
        agentRunSteps={agentPlan.run?.steps}
      />

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
            agentPlan={agentPlan}
            onFollowUpQueriesViewed={() =>
              setAgenticViews((v) => ({ ...v, follow_up_queries_viewed: true }))
            }
            onContradictoryViewed={() =>
              setAgenticViews((v) => ({ ...v, contradictory_evidence_viewed: true }))
            }
            onAgentPlanViewed={handleAgentPlanViewed}
          />
          <DecisionForm
            alertId={selectedAlertId}
            investigation={investigation}
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

"""Pydantic models for TrustOps API requests and responses."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

TrustCalibrationLevel = Literal["low", "moderate", "high"]
BiasRiskLevel = Literal["Low", "Moderate", "High"]


class HealthResponse(BaseModel):
    status: str = "ok"
    splunk_configured: bool = False
    splunk_reachable: bool | None = None
    detail: str | None = None
    mcp_configured: bool = False
    mcp_detail: str | None = None


class AlertModel(BaseModel):
    alert_id: str
    title: str
    severity: str
    status: str
    user: str
    summary: str
    mitre_tactics: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    related_src_ips: list[str] = Field(default_factory=list)
    scenario: str


class AuthEventModel(BaseModel):
    """Normalized auth row returned to the UI."""

    _time: str | None = None
    user: str | None = None
    src_ip: str | None = None
    dest_host: str | None = None
    action: str | None = None
    geo_country: str | None = None
    auth_method: str | None = None
    risk_score: str | None = None
    event_type: str | None = None
    alert_id: str | None = None
    scenario: str | None = None


class FollowUpQuery(BaseModel):
    title: str
    purpose: str
    spl: str
    priority: Literal["high", "medium", "low"]


class ContradictoryEvidence(BaseModel):
    possible_benign_explanations: list[str]
    recommended_validation_steps: list[str]
    evidence_gaps: list[str]


class MitreAttackMapping(BaseModel):
    tactic: str
    technique: str
    technique_id: str
    rationale: str
    description: str | None = None
    detection: str | None = None
    data_sources: list[str] | None = None
    platforms: list[str] | None = None
    url: str | None = None
    validated: bool = False
    enrichment_source: str = "local_fallback"
    note: str | None = None


AgentStepStatus = Literal["pending", "running", "complete", "error"]
AgentRunStatus = Literal["running", "complete", "error"]


class AgentStepResult(BaseModel):
    agent_name: str
    objective: str
    status: AgentStepStatus = "pending"
    started_at: str
    completed_at: str = ""
    tools_used: list[str] = Field(default_factory=list)
    input_summary: str = ""
    output_summary: str = ""
    evidence: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    error: str | None = None
    mitre_mappings: list[MitreAttackMapping] | None = None
    mitre_techniques: list[str] | None = None
    mitre_tactics: list[str] | None = None


class AgentRunResult(BaseModel):
    run_id: str
    alert_id: str
    status: AgentRunStatus = "running"
    started_at: str
    completed_at: str = ""
    plan_summary: str = ""
    steps: list[AgentStepResult] = Field(default_factory=list)
    final_summary: str = ""
    telemetry_logged: bool = False
    telemetry_steps_logged: int = 0
    telemetry_warning: str | None = None


class AgentStepTelemetryRow(BaseModel):
    timestamp: str | None = None
    run_id: str | None = None
    alert_id: str | None = None
    agent_name: str | None = None
    status: str | None = None
    tools_used: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    evidence_count: int | None = None
    recommendation_count: int | None = None
    output_summary: str | None = None
    error: str | None = None


class AgentRunTelemetryResponse(BaseModel):
    run_id: str
    spl_query_used: str
    steps: list[AgentStepTelemetryRow]


class AgentRunCountByAgent(BaseModel):
    agent_name: str
    count: int


class AgentRunCountByStatus(BaseModel):
    status: str
    count: int


class AgentRunAvgDuration(BaseModel):
    agent_name: str
    avg_duration_ms: float


class AgentRunsSummaryResponse(BaseModel):
    count_by_agent: list[AgentRunCountByAgent]
    count_by_status: list[AgentRunCountByStatus]
    avg_duration_by_agent: list[AgentRunAvgDuration]
    recent_run_ids: list[str]


class AgentPlanAgent(BaseModel):
    """Legacy simplified agent card (deprecated; prefer AgentRunResult)."""

    agent_name: str
    objective: str
    status: Literal["complete", "pending", "running"] = "complete"
    output_summary: str


class AgentPlanResponse(BaseModel):
    """Legacy plan response (deprecated; prefer AgentRunResult)."""

    alert_id: str
    plan_summary: str
    agents: list[AgentPlanAgent]


class FollowUpQueriesResponse(BaseModel):
    alert_id: str
    queries: list[FollowUpQuery]


class InvestigationResponse(BaseModel):
    alert: AlertModel
    events: list[AuthEventModel]
    investigation_summary: str
    key_evidence: list[str]
    ai_recommendation: str
    recommended_severity: str
    recommended_actions: list[str]
    confidence_rationale: str
    spl_query_used: str
    trust_calibration_notice: str = ""
    trust_calibration_level: TrustCalibrationLevel = "low"
    follow_up_queries: list[FollowUpQuery] = Field(default_factory=list)
    contradictory_evidence: ContradictoryEvidence | None = None
    mitre_attack_mappings: list[MitreAttackMapping] | None = None
    mitre_attack_rationale: str | None = None


class AuthEventsResponse(BaseModel):
    alert_id: str
    spl_query_used: str
    events: list[AuthEventModel]


class DecisionRowModel(BaseModel):
    timestamp: str | None = None
    alert_id: str | None = None
    analyst: str | None = None
    ai_recommendation: str | None = None
    analyst_decision: str | None = None
    final_severity: str | None = None
    confidence_score: str | None = None
    trust_score: str | None = None
    time_to_decision_seconds: str | None = None
    ai_recommendation_status: str | None = None
    evidence_reviewed_count: str | None = None
    sop_followed: str | None = None
    notes: str | None = None


class DecisionsForAlertResponse(BaseModel):
    alert_id: str
    spl_query_used: str
    decisions: list[DecisionRowModel]


class DecisionCreate(BaseModel):
    client_decision_id: str = Field(..., min_length=8, max_length=64)
    alert_id: str
    analyst: str
    ai_recommendation: str
    analyst_decision: str
    final_severity: str
    confidence_score: int = Field(..., ge=1, le=5)
    trust_score: int = Field(..., ge=1, le=5)
    time_to_decision_seconds: int = Field(..., ge=0)
    ai_recommendation_status: Literal["accepted", "modified", "rejected"]
    evidence_reviewed_count: int = Field(..., ge=0)
    sop_followed: bool
    notes: str = ""
    evidence_checklist: str = ""
    supporting_evidence: str = Field(..., min_length=1, max_length=4000)
    contradicting_evidence: str = Field(..., min_length=1, max_length=4000)
    agent_plan_viewed: bool = False
    follow_up_queries_viewed: bool = False
    contradictory_evidence_viewed: bool = False

    @field_validator("alert_id")
    @classmethod
    def alert_id_shape(cls, v: str) -> str:
        if not v or len(v) > 128:
            raise ValueError("alert_id must be 1–128 characters")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
        if not set(v).issubset(allowed):
            raise ValueError("alert_id contains invalid characters")
        return v


class DecisionLogged(DecisionCreate):
    """Decision as stored (includes server-side timestamp and calibration fields)."""

    timestamp: str
    automation_bias_risk_score: int = 0
    automation_bias_risk_level: BiasRiskLevel = "Low"
    feedback_message: str = ""
    learning_point: str = ""


class DecisionSubmitResponse(BaseModel):
    success: bool = True
    decision: DecisionLogged
    automation_bias_risk_score: int
    automation_bias_risk_level: BiasRiskLevel
    feedback_message: str
    learning_point: str


class DecisionSummaryRow(BaseModel):
    ai_recommendation_status: str
    decision_count: int
    avg_confidence: float | None = None
    avg_trust: float | None = None
    avg_time_to_decision: float | None = None
    avg_automation_bias_risk_score: float | None = None


class DecisionSummaryResponse(BaseModel):
    rows: list[DecisionSummaryRow]


class SplunkErrorModel(BaseModel):
    error: str
    detail: str | None = None


class SaiaExplainRequest(BaseModel):
    spl: str = Field(..., min_length=1, max_length=5000)
    additional_context: str | None = Field(default=None, max_length=2000)


class SaiaGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    alert_id: str | None = Field(default=None, max_length=128)
    spl_only: bool = False
    additional_context: str | None = Field(default=None, max_length=2000)


class SaiaSplResponse(BaseModel):
    text: str
    source: Literal["saia", "fallback"]
    generated_spl: str | None = None


class AlertChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)
    include_context: bool = True


class AlertChatResponse(BaseModel):
    conversation_id: str
    alert_id: str
    answer: str
    evidence_used: list[str] = Field(default_factory=list)
    suggested_spl: str | None = None
    source: Literal["splunk_ai_assistant", "local_fallback"]
    safety_note: str

from __future__ import annotations

from decimal import Decimal

from olive.operations.schemas import (
    AnomalyDecision,
    AnomalyObservation,
    GuardedMlDecision,
    HardeningCheck,
    MlRecommendation,
    MobileAction,
    MobileControlDecision,
    MobileControlRequest,
    ProductionReleaseDecision,
)


class OperationsEngine:
    """Fail-closed operational controls for the final roadmap phases."""

    def authorize_mobile_control(self, request: MobileControlRequest) -> MobileControlDecision:
        if request.action is MobileAction.VIEW:
            return MobileControlDecision(permitted=True, requires_web=False, reason="VIEW_ALLOWED")
        if request.action is MobileAction.CHANGE_CONFIGURATION:
            return MobileControlDecision(
                permitted=False, requires_web=True, reason="COMPLEX_CONFIGURATION_WEB_ONLY"
            )
        if request.role not in {"RISK_MANAGER", "ADMIN", "SUPER_ADMIN"}:
            return MobileControlDecision(
                permitted=False, requires_web=False, reason="ROLE_NOT_AUTHORIZED"
            )
        if not request.mfa_verified:
            return MobileControlDecision(permitted=False, requires_web=False, reason="MFA_REQUIRED")
        if request.action is MobileAction.PAUSE_STRATEGY and not request.strategy_key:
            return MobileControlDecision(
                permitted=False, requires_web=False, reason="STRATEGY_REQUIRED"
            )
        return MobileControlDecision(
            permitted=True, requires_web=False, reason="EMERGENCY_CONTROL_AUTHORIZED"
        )

    def guard_ml_recommendation(
        self, recommendation: MlRecommendation, hard_risk_approved: bool
    ) -> GuardedMlDecision:
        reasons: list[str] = []
        if not hard_risk_approved:
            reasons.append("HARD_RISK_REJECTED")
        if recommendation.risk_multiplier > 1:
            reasons.append("ML_CANNOT_INCREASE_RISK")
        if recommendation.confidence < Decimal("0.6"):
            reasons.append("LOW_MODEL_CONFIDENCE")
        accepted = not reasons
        multiplier = min(recommendation.risk_multiplier, Decimal("1")) if accepted else Decimal("0")
        return GuardedMlDecision(
            applied_multiplier=multiplier,
            accepted=accepted,
            reasons=tuple(reasons) if reasons else ("ML_RECOMMENDATION_GUARDED",),
        )

    def detect_anomaly(self, observation: AnomalyObservation) -> AnomalyDecision:
        score = abs(observation.value - observation.baseline_mean) / observation.baseline_stddev
        return AnomalyDecision(
            metric=observation.metric,
            z_score=score.quantize(Decimal("0.0001")),
            anomalous=score >= observation.threshold_z,
        )

    def approve_production_release(self, checks: list[HardeningCheck]) -> ProductionReleaseDecision:
        required_names = {
            "scalability",
            "high-availability",
            "disaster-recovery",
            "secrets",
            "resilience",
            "observability",
            "incident-response",
            "penetration-test",
            "compliance-review",
        }
        provided = {check.name for check in checks}
        failures = [check.name for check in checks if check.mandatory and not check.passed]
        failures.extend(sorted(required_names - provided))
        unique_failures = tuple(dict.fromkeys(failures))
        return ProductionReleaseDecision(
            approved=not unique_failures,
            failed_checks=unique_failures,
            checks=tuple(checks),
        )

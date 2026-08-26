from decimal import Decimal

from olive.operations.engine import OperationsEngine
from olive.operations.schemas import (
    AnomalyObservation,
    HardeningCheck,
    MlRecommendation,
    MobileAction,
    MobileControlRequest,
)


def test_mobile_view_is_available() -> None:
    result = OperationsEngine().authorize_mobile_control(
        MobileControlRequest(
            user_id="u", role="VIEWER", mfa_verified=False, action=MobileAction.VIEW
        )
    )
    assert result.permitted is True


def test_mobile_configuration_stays_web_first() -> None:
    result = OperationsEngine().authorize_mobile_control(
        MobileControlRequest(
            user_id="u",
            role="SUPER_ADMIN",
            mfa_verified=True,
            action=MobileAction.CHANGE_CONFIGURATION,
        )
    )
    assert result.permitted is False and result.requires_web is True


def test_mobile_emergency_control_requires_role_and_mfa() -> None:
    no_role = OperationsEngine().authorize_mobile_control(
        MobileControlRequest(
            user_id="u", role="VIEWER", mfa_verified=True, action=MobileAction.EMERGENCY_HALT
        )
    )
    no_mfa = OperationsEngine().authorize_mobile_control(
        MobileControlRequest(
            user_id="u", role="ADMIN", mfa_verified=False, action=MobileAction.EMERGENCY_HALT
        )
    )
    assert no_role.reason == "ROLE_NOT_AUTHORIZED" and no_mfa.reason == "MFA_REQUIRED"


def test_mobile_strategy_pause_requires_target() -> None:
    result = OperationsEngine().authorize_mobile_control(
        MobileControlRequest(
            user_id="u", role="RISK_MANAGER", mfa_verified=True, action=MobileAction.PAUSE_STRATEGY
        )
    )
    assert result.permitted is False and result.reason == "STRATEGY_REQUIRED"


def test_ml_cannot_override_hard_risk_rejection() -> None:
    result = OperationsEngine().guard_ml_recommendation(
        MlRecommendation(
            model_key="rank",
            model_version="1",
            risk_multiplier=Decimal("0.5"),
            confidence=Decimal("0.9"),
            explanation=("good",),
        ),
        False,
    )
    assert result.accepted is False and result.applied_multiplier == 0


def test_ml_cannot_increase_risk() -> None:
    result = OperationsEngine().guard_ml_recommendation(
        MlRecommendation(
            model_key="rank",
            model_version="1",
            risk_multiplier=Decimal("1.2"),
            confidence=Decimal("0.9"),
            explanation=("good",),
        ),
        True,
    )
    assert result.accepted is False and "ML_CANNOT_INCREASE_RISK" in result.reasons


def test_anomaly_detection_is_deterministic() -> None:
    result = OperationsEngine().detect_anomaly(
        AnomalyObservation(
            metric="slippage",
            value=Decimal("5"),
            baseline_mean=Decimal("1"),
            baseline_stddev=Decimal("1"),
            threshold_z=Decimal("3"),
        )
    )
    assert result.z_score == Decimal("4.0000") and result.anomalous is True


def all_checks() -> list[HardeningCheck]:
    names = (
        "scalability",
        "high-availability",
        "disaster-recovery",
        "secrets",
        "resilience",
        "observability",
        "incident-response",
        "penetration-test",
        "compliance-review",
    )
    return [HardeningCheck(name=name, passed=True, evidence="verified") for name in names]


def test_release_fails_when_required_check_is_missing() -> None:
    result = OperationsEngine().approve_production_release(all_checks()[:-1])
    assert result.approved is False and result.failed_checks == ("compliance-review",)


def test_release_passes_only_with_complete_evidence() -> None:
    result = OperationsEngine().approve_production_release(all_checks())
    assert result.approved is True and result.failed_checks == ()

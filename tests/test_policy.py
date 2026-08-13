from src.artifacts.schema import (
    ArtifactStep,
    StepType,
)
from src.policy.engine import PolicyEngine


def make_policy():
    return PolicyEngine(
        allowed_hosts=[
            "127.0.0.1",
            "localhost",
        ],
        allowed_actions=[
            StepType.TYPE,
            StepType.CLICK,
            StepType.EXTRACT,
        ],
    )


def test_allowed_host():
    policy = make_policy()

    decision = policy.check_navigation(
        "http://127.0.0.1:5000/"
    )

    assert decision.allowed is True
    assert decision.requires_human is False


def test_disallowed_host():
    policy = make_policy()

    decision = policy.check_navigation(
        "https://example.com"
    )

    assert decision.allowed is False
    assert "not in the allowlist" in decision.reason


def test_safe_action_is_allowed():
    policy = make_policy()

    step = ArtifactStep(
        id="step_1",
        step_type=StepType.CLICK,
        description="Submit the member search.",
    )

    decision = policy.check_step(step)

    assert decision.allowed is True
    assert decision.requires_human is False


def test_risky_action_requires_human():
    policy = make_policy()

    step = ArtifactStep(
        id="step_1",
        step_type=StepType.CLICK,
        description=(
            "Confirm transaction for the member."
        ),
    )

    decision = policy.check_step(step)

    assert decision.allowed is False
    assert decision.requires_human is True
    assert (
        "confirm transaction"
        in decision.reason.lower()
    )
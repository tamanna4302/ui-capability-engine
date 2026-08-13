from dataclasses import dataclass
from urllib.parse import urlparse

from src.artifacts.schema import ArtifactStep, StepType


@dataclass
class PolicyDecision:
    allowed: bool
    requires_human: bool
    reason: str


class PolicyEngine:
    def __init__(
        self,
        allowed_hosts: list[str],
        allowed_actions: list[StepType],
        risky_keywords: list[str] | None = None,
    ):
        self.allowed_hosts = allowed_hosts
        self.allowed_actions = allowed_actions

        self.risky_keywords = risky_keywords or [
            "delete",
            "transfer",
            "submit payment",
            "close account",
            "open account",
            "confirm transaction",
        ]

    def check_navigation(
        self,
        url: str,
    ) -> PolicyDecision:
        parsed = urlparse(url)

        host = parsed.hostname

        if host not in self.allowed_hosts:
            return PolicyDecision(
                allowed=False,
                requires_human=False,
                reason=(
                    f"Host '{host}' is not "
                    "in the allowlist."
                ),
            )

        return PolicyDecision(
            allowed=True,
            requires_human=False,
            reason="Navigation target is allowed.",
        )

    def check_step(
        self,
        step: ArtifactStep,
    ) -> PolicyDecision:
        if step.step_type not in self.allowed_actions:
            return PolicyDecision(
                allowed=False,
                requires_human=False,
                reason=(
                    f"Action '{step.step_type.value}' "
                    "is not permitted."
                ),
            )

        description = (
            step.description or ""
        ).lower()

        for keyword in self.risky_keywords:
            if keyword in description:
                return PolicyDecision(
                    allowed=False,
                    requires_human=True,
                    reason=(
                        "Potentially risky or "
                        "irreversible action detected: "
                        f"'{keyword}'."
                    ),
                )

        return PolicyDecision(
            allowed=True,
            requires_human=False,
            reason="Action permitted.",
        )
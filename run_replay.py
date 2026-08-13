from pathlib import Path

from src.artifacts.schema import (
    CapabilityArtifact,
    StepType,
)
from src.escalation.handoff import (
    HumanHandoffManager,
)
from src.observability.logger import (
    RunLogger,
)
from src.policy.engine import (
    PolicyEngine,
)
from src.replay.engine import (
    ReplayEngine,
)
from src.surface.playwright_surface import (
    PlaywrightSurface,
)


ARTIFACT_PATH = Path(
    "capabilities/get_savings_balance.v1.json"
)


def main():
    artifact_json = (
        ARTIFACT_PATH.read_text(
            encoding="utf-8"
        )
    )

    artifact = (
        CapabilityArtifact
        .model_validate_json(
            artifact_json
        )
    )

    surface = PlaywrightSurface(
        headless=False
    )

    policy = PolicyEngine(
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

    handoff = HumanHandoffManager(
        evidence_dir="evidence/handoff"
    )

    logger = RunLogger(
        run_type="replay"
    )

    try:
        surface.open(
            artifact.entry_point
        )

        logger.log(
            "run_started",
            capability=(
                artifact.capability_name
            ),
            artifact_version=(
                artifact.capability_version
            ),
            entry_point=(
                artifact.entry_point
            ),
            inputs={
                "member_id": "[REDACTED]"
            },
        )

        engine = ReplayEngine(
            surface=surface,
            policy=policy,
            handoff=handoff,
        )

        result = engine.replay(
            artifact=artifact,
            inputs={
                "member_id": "67890"
            },
        )

        logger.log(
            "run_completed",
            status=result.get(
                "status"
            ),
            result=result,
        )

        if result.get(
            "status"
        ) not in {
            "success",
            "business_outcome",
        }:
            screenshot_path = (
                logger.save_screenshot(
                    surface,
                    "failure",
                )
            )

            logger.log(
                "failure_evidence",
                screenshot=(
                    screenshot_path
                ),
            )

        print(
            "\n=============================="
        )
        print("REPLAY RESULT")
        print(
            "=============================="
        )

        print(result)

        print(
            "\nEvidence saved to:"
        )
        print(
            logger.run_dir
        )

    finally:
        surface.close()


if __name__ == "__main__":
    main()
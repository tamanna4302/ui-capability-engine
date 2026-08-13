from pathlib import Path

from src.agent.discovery import DiscoveryAgent
from src.artifacts.builder import ArtifactBuilder
from src.observability.logger import RunLogger
from src.surface.playwright_surface import PlaywrightSurface


TARGET_URL = "http://127.0.0.1:5000"

GOAL = (
    "Look up member 12345 and return "
    "their current savings balance."
)


def main():
    surface = PlaywrightSurface(
        headless=False
    )

    logger = RunLogger(
        run_type="discovery"
    )

    try:
        surface.open(TARGET_URL)

        logger.log(
            "discovery_started",
            goal=GOAL,
            target=TARGET_URL,
            model="claude-sonnet-5",
        )

        agent = DiscoveryAgent(
            surface=surface,
            model="claude-sonnet-5",
            max_steps=8,
        )

        result = agent.run(GOAL)

        logger.log(
            "discovery_completed",
            status=result.get("status"),
            result=result.get("result"),
            step_count=len(
                result.get("steps", [])
            ),
        )

        #
        # Save a sanitized trace of what
        # discovery actually did.
        #
        for recorded_step in result.get(
            "steps",
            [],
        ):
            action = recorded_step.get(
                "action",
                {},
            )

            action_type = action.get(
                "action_type"
            )

            if hasattr(
                action_type,
                "value",
            ):
                action_type = (
                    action_type.value
                )

            logger.log(
                "discovery_step",
                step=recorded_step.get(
                    "step"
                ),
                action_type=action_type,
                reason=action.get(
                    "reason"
                ),
            )

        if result["status"] != "success":
            screenshot_path = (
                logger.save_screenshot(
                    surface,
                    "discovery_failure",
                )
            )

            logger.log(
                "failure_evidence",
                screenshot=screenshot_path,
            )

            print(
                "\n=============================="
            )
            print("DISCOVERY FAILED")
            print(
                "=============================="
            )
            print(result)

            return

        #
        # Save evidence of the final state.
        #
        final_screenshot = (
            logger.save_screenshot(
                surface,
                "discovery_success",
            )
        )

        logger.log(
            "success_evidence",
            screenshot=final_screenshot,
        )

        builder = ArtifactBuilder()

        artifact = (
            builder.build_from_discovery(
                goal=GOAL,
                discovery_result=result,
            )
        )

        output_directory = Path(
            "capabilities"
        )

        output_directory.mkdir(
            exist_ok=True
        )

        output_path = (
            output_directory
            / "get_savings_balance.v1.json"
        )

        output_path.write_text(
            artifact.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        logger.log(
            "artifact_created",
            capability=(
                artifact.capability_name
            ),
            capability_version=(
                artifact.capability_version
            ),
            artifact_path=str(
                output_path
            ),
        )

        print(
            "\n=============================="
        )
        print("FINAL RESULT")
        print(
            "=============================="
        )

        print(
            {
                "status": result["status"],
                "result": result.get(
                    "result"
                ),
            }
        )

        print(
            "\n=============================="
        )
        print("CAPABILITY ARTIFACT")
        print(
            "=============================="
        )

        print(
            f"Saved to: {output_path}"
        )

        print(
            "\nDiscovery evidence saved to:"
        )

        print(
            logger.run_dir
        )

    finally:
        surface.close()


if __name__ == "__main__":
    main()
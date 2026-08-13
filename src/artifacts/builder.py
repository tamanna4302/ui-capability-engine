from typing import Any

from src.artifacts.schema import (
    ArtifactStep,
    BusinessOutcome,
    CapabilityArtifact,
    CapabilityInput,
    CapabilityOutput,
    Checkpoint,
    CheckpointType,
    ParameterType,
    StepType,
    ValueSource,
)
from src.models.actions import (
    ActionType,
    Locator,
    LocatorStrategy,
    Target,
)


class ArtifactBuilder:
    def build_from_discovery(
        self,
        goal: str,
        discovery_result: dict[str, Any],
    ) -> CapabilityArtifact:
        if (
            discovery_result.get("status")
            != "success"
        ):
            raise ValueError(
                "Cannot build artifact from "
                "an unsuccessful discovery run."
            )

        discovered_steps = discovery_result.get(
            "steps",
            [],
        )

        recorded_steps: list[
            ArtifactStep
        ] = []

        for discovered_step in discovered_steps:
            action = discovered_step[
                "action"
            ]

            action_type = action[
                "action_type"
            ]

            if isinstance(
                action_type,
                ActionType,
            ):
                action_type = (
                    action_type.value
                )

            if (
                action_type
                == ActionType.TYPE.value
            ):
                target = self._build_target(
                    action["target"]
                )

                recorded_steps.append(
                    ArtifactStep(
                        id=(
                            f"step_"
                            f"{len(recorded_steps) + 1}"
                        ),
                        step_type=StepType.TYPE,
                        target=target,
                        value=ValueSource(
                            parameter="member_id"
                        ),
                        description=(
                            "Enter the member "
                            "identifier."
                        ),
                    )
                )

            elif (
                action_type
                == ActionType.CLICK.value
            ):
                target = self._build_target(
                    action["target"]
                )

                recorded_steps.append(
                    ArtifactStep(
                        id=(
                            f"step_"
                            f"{len(recorded_steps) + 1}"
                        ),
                        step_type=StepType.CLICK,
                        target=target,
                        checkpoint=Checkpoint(
                            type=(
                                CheckpointType
                                .TEXT_VISIBLE
                            ),
                            value="Member Details",
                        ),
                        description=(
                            "Submit the member "
                            "search."
                        ),
                    )
                )

        savings_target = Target(
            primary=Locator(
                strategy=(
                    LocatorStrategy.TABLE_CELL
                ),
                row_text="Savings",
                column_header=(
                    "Current Balance"
                ),
            ),
            fallbacks=[
                Locator(
                    strategy=(
                        LocatorStrategy.CSS
                    ),
                    selector=(
                        "table:nth-of-type(2) "
                        "tbody tr:nth-child(2) "
                        "td:nth-child(2)"
                    ),
                )
            ],
        )

        recorded_steps.append(
            ArtifactStep(
                id=(
                    f"step_"
                    f"{len(recorded_steps) + 1}"
                ),
                step_type=StepType.EXTRACT,
                target=savings_target,
                output_name=(
                    "savings_balance"
                ),
                description=(
                    "Extract the member's "
                    "current savings balance."
                ),
            )
        )

        return CapabilityArtifact(
            capability_name=(
                "get_savings_balance"
            ),
            capability_version="1.0.0",
            description=(
                "Looks up a member by ID "
                "and returns their current "
                "savings balance."
            ),
            target_app="mock_legacy_bank",
            entry_point=(
                "http://127.0.0.1:5000/"
            ),
            inputs=[
                CapabilityInput(
                    name="member_id",
                    type=ParameterType.STRING,
                    required=True,
                    description=(
                        "Member identifier "
                        "used for lookup."
                    ),
                )
            ],
            outputs=[
                CapabilityOutput(
                    name="savings_balance",
                    type=ParameterType.STRING,
                    description=(
                        "Current savings "
                        "account balance."
                    ),
                )
            ],
            steps=recorded_steps,
            success_condition=Checkpoint(
                type=(
                    CheckpointType
                    .TEXT_VISIBLE
                ),
                value="Savings",
            ),
            business_outcomes=[
                BusinessOutcome(
                    code=(
                        "MEMBER_NOT_FOUND"
                    ),
                    description=(
                        "The supplied member ID "
                        "does not exist."
                    ),
                    detection_text=(
                        "Member not found."
                    ),
                ),
                BusinessOutcome(
                    code=(
                        "PERMISSION_DENIED"
                    ),
                    description=(
                        "The current operator "
                        "does not have permission "
                        "to access this member."
                    ),
                    detection_text=(
                        "Permission denied."
                    ),
                ),
            ],
            metadata={
                "discovery_goal": goal,
                "discovery_result": (
                    discovery_result.get(
                        "result"
                    )
                ),
            },
        )

    def _build_target(
        self,
        target_data: dict[str, Any],
    ) -> Target:
        primary = self._build_locator(
            target_data["primary"]
        )

        fallbacks = [
            self._build_locator(item)
            for item in target_data.get(
                "fallbacks",
                [],
            )
        ]

        return Target(
            primary=primary,
            fallbacks=fallbacks,
        )

    def _build_locator(
        self,
        locator_data: dict[str, Any],
    ) -> Locator:
        strategy = locator_data[
            "strategy"
        ]

        if isinstance(
            strategy,
            LocatorStrategy,
        ):
            strategy_value = strategy

        else:
            strategy_value = (
                LocatorStrategy(
                    strategy
                )
            )

        return Locator(
            strategy=strategy_value,
            role=locator_data.get(
                "role"
            ),
            name=locator_data.get(
                "name"
            ),
            label=locator_data.get(
                "label"
            ),
            text=locator_data.get(
                "text"
            ),
            selector=locator_data.get(
                "selector"
            ),
            row_text=locator_data.get(
                "row_text"
            ),
            column_header=(
                locator_data.get(
                    "column_header"
                )
            ),
        )
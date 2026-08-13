from typing import Any

from src.artifacts.schema import (
    CapabilityArtifact,
    Checkpoint,
    CheckpointType,
    StepType,
)
from src.escalation.handoff import (
    HumanHandoffManager,
)
from src.policy.engine import PolicyEngine
from src.surface.base import Surface


class ReplayEngine:
    def __init__(
        self,
        surface: Surface,
        policy: PolicyEngine,
        handoff: HumanHandoffManager | None = None,
        max_retries: int = 1,
    ):
        self.surface = surface
        self.policy = policy
        self.handoff = handoff
        self.max_retries = max_retries

    def replay(
        self,
        artifact: CapabilityArtifact,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_inputs(
            artifact,
            inputs,
        )

        navigation_decision = (
            self.policy.check_navigation(
                artifact.entry_point
            )
        )

        if not navigation_decision.allowed:
            return {
                "status": "policy_blocked",
                "code": "NAVIGATION_NOT_ALLOWED",
                "message": (
                    navigation_decision.reason
                ),
                "outputs": {},
            }

        outputs: dict[str, Any] = {}

        for step in artifact.steps:
            print(
                f"\nREPLAYING {step.id}: "
                f"{step.step_type.value}"
            )

            policy_decision = (
                self.policy.check_step(step)
            )

            if (
                policy_decision.requires_human
            ):
                handoff_result = (
                    self._handle_human_handoff(
                        artifact=artifact,
                        step=step,
                        reason=(
                            policy_decision.reason
                        ),
                    )
                )

                if (
                    handoff_result["status"]
                    != "resumed"
                ):
                    return {
                        "status": "needs_human",
                        "code": (
                            "HUMAN_HANDOFF_FAILED"
                        ),
                        "step": step.id,
                        "message": (
                            handoff_result.get(
                                "reason",
                                "Human intervention "
                                "could not complete.",
                            )
                        ),
                        "outputs": outputs,
                    }

                if step.checkpoint:
                    if not self._verify_checkpoint(
                        step.checkpoint
                    ):
                        return {
                            "status": "hard_failure",
                            "code": (
                                "POST_HANDOFF_"
                                "CHECKPOINT_FAILED"
                            ),
                            "step": step.id,
                            "message": (
                                "Human returned "
                                "control, but the "
                                "expected checkpoint "
                                "was not reached."
                            ),
                            "outputs": outputs,
                        }

                print(
                    "Human-completed step "
                    "verified. Resuming replay."
                )

                continue

            if not policy_decision.allowed:
                return {
                    "status": "policy_blocked",
                    "code": "ACTION_NOT_ALLOWED",
                    "step": step.id,
                    "message": (
                        policy_decision.reason
                    ),
                    "outputs": outputs,
                }

            result = (
                self._run_step_with_recovery(
                    artifact=artifact,
                    step=step,
                    inputs=inputs,
                )
            )

            if (
                result["status"]
                != "success"
            ):
                result["outputs"] = outputs
                return result

            if step.output_name:
                outputs[
                    step.output_name
                ] = result.get("value")

        if not self._verify_checkpoint(
            artifact.success_condition
        ):
            business_outcome = (
                self._detect_business_outcome(
                    artifact
                )
            )

            if business_outcome:
                return {
                    "status": (
                        "business_outcome"
                    ),
                    "code": (
                        business_outcome.code
                    ),
                    "message": (
                        business_outcome
                        .description
                    ),
                    "outputs": outputs,
                }

            return {
                "status": "hard_failure",
                "code": (
                    "FINAL_CHECKPOINT_FAILED"
                ),
                "message": (
                    "Final success condition "
                    "was not satisfied."
                ),
                "outputs": outputs,
            }

        return {
            "status": "success",
            "outputs": outputs,
        }

    def _handle_human_handoff(
        self,
        artifact: CapabilityArtifact,
        step,
        reason: str,
    ) -> dict[str, Any]:
        if self.handoff is None:
            return {
                "status": "failed",
                "reason": (
                    "No human handoff manager "
                    "is configured."
                ),
            }

        return (
            self.handoff
            .request_intervention(
                surface=self.surface,
                capability_name=(
                    artifact.capability_name
                ),
                step_id=step.id,
                reason=reason,
            )
        )

    def _run_step_with_recovery(
        self,
        artifact: CapabilityArtifact,
        step,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        attempt = 0

        while (
            attempt <= self.max_retries
        ):
            try:
                value = self._execute_step(
                    step=step,
                    inputs=inputs,
                )

                if step.checkpoint:
                    if self._verify_checkpoint(
                        step.checkpoint
                    ):
                        return {
                            "status": "success",
                            "value": value,
                        }

                    business_outcome = (
                        self
                        ._detect_business_outcome(
                            artifact
                        )
                    )

                    if business_outcome:
                        return {
                            "status": (
                                "business_outcome"
                            ),
                            "code": (
                                business_outcome.code
                            ),
                            "message": (
                                business_outcome
                                .description
                            ),
                        }

                    if (
                        self
                        ._is_transient_error()
                    ):
                        if (
                            attempt
                            < self.max_retries
                        ):
                            print(
                                "Recoverable "
                                "condition "
                                "detected. "
                                "Retrying..."
                            )

                            (
                                self
                                ._recover_to_entry_state(
                                    artifact,
                                    inputs,
                                )
                            )

                            attempt += 1
                            continue

                        return {
                            "status": (
                                "recoverable_error"
                            ),
                            "code": (
                                "TRANSIENT_ERROR"
                            ),
                            "message": (
                                "Transient condition "
                                "persisted after "
                                "retry."
                            ),
                        }

                    return {
                        "status": "hard_failure",
                        "code": (
                            "CHECKPOINT_FAILED"
                        ),
                        "step": step.id,
                        "message": (
                            "Expected checkpoint "
                            "was not satisfied."
                        ),
                    }

                return {
                    "status": "success",
                    "value": value,
                }

            except Exception as exc:
                if (
                    self._is_transient_error()
                    and attempt
                    < self.max_retries
                ):
                    print(
                        "Recoverable condition "
                        "detected. Retrying..."
                    )

                    self._recover_to_entry_state(
                        artifact,
                        inputs,
                    )

                    attempt += 1
                    continue

                return {
                    "status": "hard_failure",
                    "code": (
                        "STEP_EXECUTION_FAILED"
                    ),
                    "step": step.id,
                    "message": str(exc),
                }

        return {
            "status": "recoverable_error",
            "code": "RETRY_EXHAUSTED",
            "message": (
                "Retry limit exhausted."
            ),
        }

    def _recover_to_entry_state(
        self,
        artifact: CapabilityArtifact,
        inputs: dict[str, Any],
    ) -> None:
        self.surface.close()

        self.surface.open(
            artifact.entry_point
        )

        first_step = artifact.steps[0]

        if (
            first_step.step_type
            == StepType.TYPE
        ):
            self._execute_step(
                first_step,
                inputs,
            )

    def _is_transient_error(
        self,
    ) -> bool:
        observation = (
            self.surface.observe()
        )

        text = observation.get(
            "visible_text",
            "",
        )

        return (
            "Temporary service error"
            in text
        )

    def _validate_inputs(
        self,
        artifact: CapabilityArtifact,
        inputs: dict[str, Any],
    ) -> None:
        for parameter in artifact.inputs:
            if (
                parameter.required
                and parameter.name
                not in inputs
            ):
                raise ValueError(
                    "Missing required input: "
                    f"{parameter.name}"
                )

    def _execute_step(
        self,
        step,
        inputs: dict[str, Any],
    ) -> Any:
        if (
            step.step_type
            == StepType.TYPE
        ):
            if not step.target:
                raise RuntimeError(
                    "TYPE step has no target."
                )

            if not step.value:
                raise RuntimeError(
                    "TYPE step has no value."
                )

            if step.value.parameter:
                parameter_name = (
                    step.value.parameter
                )

                if (
                    parameter_name
                    not in inputs
                ):
                    raise RuntimeError(
                        "Missing parameter: "
                        f"{parameter_name}"
                    )

                value = str(
                    inputs[
                        parameter_name
                    ]
                )

            elif (
                step.value.literal
                is not None
            ):
                value = (
                    step.value.literal
                )

            else:
                raise RuntimeError(
                    "TYPE step has no "
                    "usable value."
                )

            self.surface.type_text(
                step.target,
                value,
            )

            return None

        if (
            step.step_type
            == StepType.CLICK
        ):
            if not step.target:
                raise RuntimeError(
                    "CLICK step has no target."
                )

            self.surface.click(
                step.target
            )

            return None

        if (
            step.step_type
            == StepType.EXTRACT
        ):
            if not step.target:
                raise RuntimeError(
                    "EXTRACT step has no target."
                )

            return (
                self.surface.read_text(
                    step.target
                )
            )

        raise RuntimeError(
            "Unsupported step type: "
            f"{step.step_type}"
        )

    def _verify_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> bool:
        observation = (
            self.surface.observe()
        )

        if (
            checkpoint.type
            == CheckpointType.TEXT_VISIBLE
        ):
            return (
                checkpoint.value
                in observation.get(
                    "visible_text",
                    "",
                )
            )

        if (
            checkpoint.type
            == CheckpointType.URL_CONTAINS
        ):
            return (
                checkpoint.value
                in observation.get(
                    "url",
                    "",
                )
            )

        return False

    def _detect_business_outcome(
        self,
        artifact: CapabilityArtifact,
    ):
        observation = (
            self.surface.observe()
        )

        visible_text = observation.get(
            "visible_text",
            "",
        )

        for outcome in (
            artifact.business_outcomes
        ):
            if (
                outcome.detection_text
                in visible_text
            ):
                return outcome

        return None
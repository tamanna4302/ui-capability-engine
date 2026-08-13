from pathlib import Path
from typing import Any

from src.artifacts.schema import (
    CapabilityArtifact,
    StepType,
)
from src.policy.engine import (
    PolicyEngine,
)
from src.replay.engine import (
    ReplayEngine,
)
from src.surface.base import Surface


ARTIFACT_PATH = Path(
    "capabilities/get_savings_balance.v1.json"
)


class FakeSurface(Surface):
    def __init__(
        self,
        member_results: dict[str, str],
    ):
        self.member_results = (
            member_results
        )

        self.current_member_id = ""
        self.page_state = "search"

        self.temporary_failure_used = (
            False
        )

    def open(
        self,
        target: str,
    ) -> None:
        self.page_state = "search"

    def observe(
        self,
    ) -> dict[str, Any]:
        if self.page_state == "search":
            return {
                "url": (
                    "http://127.0.0.1:5000/"
                ),
                "title": "Member Search",
                "visible_text": (
                    "Member Search\n"
                    "Member ID\n"
                    "Search"
                ),
                "controls": [],
            }

        if (
            self.page_state
            == "not_found"
        ):
            return {
                "url": (
                    "http://127.0.0.1:5000/"
                ),
                "title": "Member Search",
                "visible_text": (
                    "Member Search\n"
                    "Member not found."
                ),
                "controls": [],
            }

        if (
            self.page_state
            == "permission_denied"
        ):
            return {
                "url": (
                    "http://127.0.0.1:5000/"
                ),
                "title": "Member Search",
                "visible_text": (
                    "Member Search\n"
                    "Permission denied."
                ),
                "controls": [],
            }

        if (
            self.page_state
            == "temporary_error"
        ):
            return {
                "url": (
                    "http://127.0.0.1:5000/"
                ),
                "title": "Member Search",
                "visible_text": (
                    "Temporary service error. "
                    "Please try again."
                ),
                "controls": [],
            }

        if self.page_state == "member":
            balance = (
                self.member_results[
                    self.current_member_id
                ]
            )

            return {
                "url": (
                    "http://127.0.0.1:5000/"
                    "member"
                ),
                "title": "Member Details",
                "visible_text": (
                    "Member Details\n"
                    "Accounts\n"
                    "Account Type\n"
                    "Current Balance\n"
                    "Savings\n"
                    f"{balance}"
                ),
                "controls": [],
            }

        raise RuntimeError(
            "Unknown fake page state."
        )

    def click(
        self,
        target,
    ) -> None:
        if (
            self.current_member_id
            == "99999"
        ):
            self.page_state = (
                "not_found"
            )

            return

        if (
            self.current_member_id
            == "77777"
        ):
            self.page_state = (
                "permission_denied"
            )

            return

        if (
            self.current_member_id
            == "55555"
            and not
            self.temporary_failure_used
        ):
            self.temporary_failure_used = (
                True
            )

            self.page_state = (
                "temporary_error"
            )

            return

        if (
            self.current_member_id
            in self.member_results
        ):
            self.page_state = "member"
            return

        self.page_state = "not_found"

    def type_text(
        self,
        target,
        value: str,
    ) -> None:
        self.current_member_id = value

    def read_text(
        self,
        target,
    ) -> str:
        if self.page_state != "member":
            raise RuntimeError(
                "Member details are "
                "not visible."
            )

        return self.member_results[
            self.current_member_id
        ]

    def screenshot(
        self,
        path: str,
    ) -> None:
        Path(path).write_text(
            "fake screenshot",
            encoding="utf-8",
        )

    def close(
        self,
    ) -> None:
        self.page_state = "search"


class BrokenSurface(FakeSurface):
    def click(
        self,
        target,
    ) -> None:
        raise RuntimeError(
            "Unable to resolve target."
        )


def load_artifact():
    return (
        CapabilityArtifact
        .model_validate_json(
            ARTIFACT_PATH.read_text(
                encoding="utf-8"
            )
        )
    )


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


def test_successful_replay():
    artifact = load_artifact()

    surface = FakeSurface(
        {
            "67890": "$823.19",
        }
    )

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
    )

    result = engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "67890"
        },
    )

    assert (
        result["status"]
        == "success"
    )

    assert (
        result["outputs"][
            "savings_balance"
        ]
        == "$823.19"
    )


def test_member_not_found():
    artifact = load_artifact()

    surface = FakeSurface({})

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
    )

    result = engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "99999"
        },
    )

    assert (
        result["status"]
        == "business_outcome"
    )

    assert (
        result["code"]
        == "MEMBER_NOT_FOUND"
    )


def test_permission_denied():
    artifact = load_artifact()

    surface = FakeSurface({})

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
    )

    result = engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "77777"
        },
    )

    assert (
        result["status"]
        == "business_outcome"
    )

    assert (
        result["code"]
        == "PERMISSION_DENIED"
    )


def test_recoverable_error_retries():
    artifact = load_artifact()

    surface = FakeSurface(
        {
            "55555": "$1,105.75",
        }
    )

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
        max_retries=1,
    )

    result = engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "55555"
        },
    )

    assert (
        result["status"]
        == "success"
    )

    assert (
        result["outputs"][
            "savings_balance"
        ]
        == "$1,105.75"
    )

    assert (
        surface.temporary_failure_used
        is True
    )


def test_hard_failure():
    artifact = load_artifact()

    surface = BrokenSurface(
        {
            "67890": "$823.19",
        }
    )

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
    )

    result = engine.replay(
        artifact=artifact,
        inputs={
            "member_id": "67890"
        },
    )

    assert (
        result["status"]
        == "hard_failure"
    )

    assert (
        result["code"]
        == "STEP_EXECUTION_FAILED"
    )

    assert (
        result["step"]
        == "step_2"
    )


def test_missing_required_input():
    artifact = load_artifact()

    surface = FakeSurface({})

    engine = ReplayEngine(
        surface=surface,
        policy=make_policy(),
    )

    try:
        engine.replay(
            artifact=artifact,
            inputs={},
        )

    except ValueError as exc:
        assert (
            "Missing required input"
            in str(exc)
        )

    else:
        raise AssertionError(
            "Expected ValueError."
        )
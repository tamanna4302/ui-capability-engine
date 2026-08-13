import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunLogger:
    def __init__(
        self,
        run_type: str,
        evidence_root: str = "evidence",
    ):
        self.run_type = run_type

        self.run_id = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%S%fZ"
        )

        self.run_dir = (
            Path(evidence_root)
            / run_type
            / self.run_id
        )

        self.run_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.events: list[
            dict[str, Any]
        ] = []

    def log(
        self,
        event_type: str,
        **data: Any,
    ) -> None:
        event = {
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "event_type": event_type,
            **data,
        }

        self.events.append(event)

        self._flush()

    def save_screenshot(
        self,
        surface,
        name: str,
    ) -> str:
        path = (
            self.run_dir
            / f"{name}.png"
        )

        surface.screenshot(
            str(path)
        )

        return str(path)

    def _flush(
        self,
    ) -> None:
        output_path = (
            self.run_dir
            / "run.json"
        )

        payload = {
            "run_id": self.run_id,
            "run_type": self.run_type,
            "events": self.events,
        }

        output_path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
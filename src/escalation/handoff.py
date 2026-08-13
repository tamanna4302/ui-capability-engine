import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.surface.base import Surface


class HumanHandoffManager:
    def __init__(
        self,
        evidence_dir: str = "evidence/handoff",
    ):
        self.evidence_dir = Path(evidence_dir)

        self.evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.human_events: list[
            dict[str, Any]
        ] = []

        self._handoff_active = False

    def request_intervention(
        self,
        surface: Surface,
        capability_name: str,
        step_id: str,
        reason: str,
    ) -> dict[str, Any]:
        page = getattr(
            surface,
            "page",
            None,
        )

        if page is None:
            return {
                "status": "failed",
                "reason": (
                    "Surface does not expose "
                    "a live controllable session."
                ),
            }

        timestamp = datetime.now(
            timezone.utc
        ).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        screenshot_path = (
            self.evidence_dir
            / (
                f"{capability_name}_"
                f"{step_id}_"
                f"{timestamp}.png"
            )
        )

        surface.screenshot(
            str(screenshot_path)
        )

        self.human_events = []
        self._handoff_active = True

        before_state = {
            "url": page.url,
            "title": page.title(),
        }

        #
        # Register Playwright-side event
        # listeners before giving control
        # to the human.
        #
        page.on(
            "request",
            self._on_request,
        )

        page.on(
            "framenavigated",
            self._on_navigation,
        )

        page.on(
            "console",
            self._on_console,
        )

        self._install_click_capture(
            page
        )

        print("\n")
        print(
            "================================"
        )
        print(
            "HUMAN INTERVENTION REQUIRED"
        )
        print(
            "================================"
        )
        print(
            f"Capability: {capability_name}"
        )
        print(
            f"Step: {step_id}"
        )
        print(
            f"Reason: {reason}"
        )
        print(
            f"Screenshot: {screenshot_path}"
        )

        print(
            "\nAutomation is PAUSED."
        )

        print(
            "Use the currently open browser "
            "window to perform the required "
            "manual action."
        )

        print(
            "\nWhen finished, return to this "
            "terminal and press ENTER."
        )

        #
        # Important:
        #
        # Do NOT block the main thread with
        # input(), because Playwright needs
        # the main thread to keep pumping
        # browser events.
        #
        resume_event = threading.Event()

        input_thread = threading.Thread(
            target=self._wait_for_resume,
            args=(resume_event,),
            daemon=True,
        )

        input_thread.start()

        #
        # Keep Playwright alive and processing
        # click/request/navigation events while
        # the human controls the browser.
        #
        while not resume_event.is_set():
            page.wait_for_timeout(200)

        #
        # Give any final browser events a
        # moment to reach our listeners.
        #
        page.wait_for_timeout(300)

        self._handoff_active = False

        after_state = {
            "url": page.url,
            "title": page.title(),
        }

        #
        # Remove the Python-side listeners
        # after control returns.
        #
        try:
            page.remove_listener(
                "request",
                self._on_request,
            )

            page.remove_listener(
                "framenavigated",
                self._on_navigation,
            )

            page.remove_listener(
                "console",
                self._on_console,
            )

        except Exception:
            pass

        evidence = {
            "capability": capability_name,
            "step": step_id,
            "reason": reason,
            "timestamp": timestamp,
            "screenshot": str(
                screenshot_path
            ),
            "before_state": before_state,
            "after_state": after_state,
            "human_events": (
                self.human_events
            ),
        }

        evidence_path = (
            self.evidence_dir
            / (
                f"{capability_name}_"
                f"{step_id}_"
                f"{timestamp}.json"
            )
        )

        evidence_path.write_text(
            json.dumps(
                evidence,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            "\nHuman control returned."
        )

        print(
            f"Recorded human events: "
            f"{len(self.human_events)}"
        )

        print(
            "Handoff evidence saved to: "
            f"{evidence_path}"
        )

        return {
            "status": "resumed",
            "events": (
                self.human_events
            ),
            "evidence_path": str(
                evidence_path
            ),
        }

    def _wait_for_resume(
        self,
        resume_event: threading.Event,
    ) -> None:
        input()
        resume_event.set()

    def _install_click_capture(
        self,
        page,
    ) -> None:
        #
        # Capture the human click through
        # the browser console.
        #
        page.evaluate(
            """
            () => {
                if (
                    window.__humanCaptureInstalled
                ) {
                    return;
                }

                window.__humanCaptureInstalled =
                    true;

                document.addEventListener(
                    "click",
                    (event) => {
                        const target =
                            event.target;

                        const payload = {
                            type: "click",
                            tag:
                                target.tagName,
                            text: (
                                target.innerText ||
                                target.value ||
                                ""
                            ).slice(
                                0,
                                100
                            ),
                            name:
                                target.getAttribute(
                                    "name"
                                ),
                            timestamp:
                                new Date()
                                .toISOString()
                        };

                        console.log(
                            "__HUMAN_EVENT__" +
                            JSON.stringify(
                                payload
                            )
                        );
                    },
                    true
                );
            }
            """
        )

    def _on_console(
        self,
        message,
    ) -> None:
        if not self._handoff_active:
            return

        try:
            text = message.text

            prefix = "__HUMAN_EVENT__"

            if not text.startswith(
                prefix
            ):
                return

            payload = json.loads(
                text[len(prefix):]
            )

            self.human_events.append(
                payload
            )

        except Exception:
            pass

    def _on_request(
        self,
        request,
    ) -> None:
        if not self._handoff_active:
            return

        #
        # Record meaningful form submission
        # requests, but do not record request
        # bodies because they could contain
        # sensitive values.
        #
        if request.method == "POST":
            self.human_events.append(
                {
                    "type": "request",
                    "method": (
                        request.method
                    ),
                    "url": request.url,
                    "timestamp": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }
            )

    def _on_navigation(
        self,
        frame,
    ) -> None:
        if not self._handoff_active:
            return

        #
        # Ignore iframe navigation.
        #
        if (
            frame.parent_frame
            is not None
        ):
            return

        self.human_events.append(
            {
                "type": "navigation",
                "url": frame.url,
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
        )
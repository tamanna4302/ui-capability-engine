import json
import os
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv

from src.models.actions import (
    Action,
    ActionType,
    Locator,
    LocatorStrategy,
    Target,
)
from src.surface.base import Surface


load_dotenv()


class DiscoveryAgent:
    def __init__(
        self,
        surface: Surface,
        model: str,
        max_steps: int = 10,
    ):
        self.surface = surface
        self.model = model
        self.max_steps = max_steps

        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set."
            )

        self.client = Anthropic(
            api_key=api_key
        )

        self.history: list[dict[str, Any]] = []

    def run(
        self,
        goal: str,
    ) -> dict[str, Any]:
        for step_number in range(
            1,
            self.max_steps + 1,
        ):
            observation = self.surface.observe()

            print(
                f"\n--- STEP {step_number} ---"
            )

            print("OBSERVATION:")
            print(
                json.dumps(
                    observation,
                    indent=2,
                )
            )

            action = self._decide(
                goal=goal,
                observation=observation,
            )

            print("\nCLAUDE ACTION:")
            print(
                action.model_dump_json(
                    indent=2
                )
            )

            self.history.append(
                {
                    "step": step_number,
                    "observation": observation,
                    "action": action.model_dump(),
                }
            )

            result = self._execute(action)

            if result is not None:
                return {
                    "status": result["status"],
                    "result": result.get("result"),
                    "steps": self.history,
                }

        return {
            "status": "failed",
            "reason": "max_steps_reached",
            "steps": self.history,
        }

    def _decide(
        self,
        goal: str,
        observation: dict[str, Any],
    ) -> Action:
        prompt = self._build_prompt(
            goal=goal,
            observation=observation,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        raw_text = self._extract_text_response(
            response.content
        )

        raw_text = self._strip_code_fence(
            raw_text
        )

        try:
            payload = json.loads(raw_text)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Claude returned invalid JSON:\n"
                f"{raw_text}"
            ) from exc

        return self._parse_action(payload)

    def _extract_text_response(
        self,
        content_blocks: list[Any],
    ) -> str:
        text_parts: list[str] = []

        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", None)

                if text:
                    text_parts.append(text)

        if not text_parts:
            raise RuntimeError(
                "Claude response contained no text block."
            )

        return "\n".join(text_parts).strip()

    def _strip_code_fence(
        self,
        raw_text: str,
    ) -> str:
        if not raw_text.startswith("```"):
            return raw_text

        lines = raw_text.splitlines()

        if (
            lines
            and lines[0].startswith("```")
        ):
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    def _build_prompt(
        self,
        goal: str,
        observation: dict[str, Any],
    ) -> str:
        return f"""
You are controlling a software interface.

Your job is to accomplish the user's goal using only
the controls and visible information in the current
observation.

GOAL:
{goal}

CURRENT OBSERVATION:
{json.dumps(observation, indent=2)}

You may choose exactly ONE action.

Supported actions:

1. type
2. click
3. read
4. complete
5. escalate

Return ONLY valid JSON.

For typing into a labeled input:

{{
  "action_type": "type",
  "target": {{
    "primary": {{
      "strategy": "label",
      "label": "Member ID"
    }}
  }},
  "value": "12345",
  "reason": "Need to enter the member ID."
}}

For clicking a button:

{{
  "action_type": "click",
  "target": {{
    "primary": {{
      "strategy": "role",
      "role": "button",
      "name": "Search"
    }},
    "fallbacks": [
      {{
        "strategy": "text",
        "text": "Search"
      }}
    ]
  }},
  "reason": "Submit the search."
}}

If the goal can already be answered from visible text:

{{
  "action_type": "complete",
  "value": "the final answer",
  "reason": "The requested information is visible."
}}

If you cannot safely determine what to do:

{{
  "action_type": "escalate",
  "reason": "Explanation of why human help is needed."
}}

Important rules:

- Do not invent controls that are not present.
- Prefer semantic locators such as label or role.
- Use visible information from the page.
- Perform only one action per response.
- Do not repeat an action if its result is already visible.
- Look at the current value of input controls.
- If an input already contains the required value,
  do not type it again.
- If the user's requested information is visible,
  complete the task.
"""

    def _parse_action(
        self,
        payload: dict[str, Any],
    ) -> Action:
        target_data = payload.get("target")

        target = None

        if target_data:
            primary = self._parse_locator(
                target_data["primary"]
            )

            fallbacks = [
                self._parse_locator(item)
                for item in target_data.get(
                    "fallbacks",
                    [],
                )
            ]

            target = Target(
                primary=primary,
                fallbacks=fallbacks,
            )

        return Action(
            action_type=ActionType(
                payload["action_type"]
            ),
            target=target,
            value=payload.get("value"),
            output_name=payload.get(
                "output_name"
            ),
            reason=payload.get("reason"),
        )

    def _parse_locator(
        self,
        payload: dict[str, Any],
    ) -> Locator:
        return Locator(
            strategy=LocatorStrategy(
                payload["strategy"]
            ),
            role=payload.get("role"),
            name=payload.get("name"),
            label=payload.get("label"),
            text=payload.get("text"),
            selector=payload.get("selector"),
        )

    def _execute(
        self,
        action: Action,
    ) -> dict[str, Any] | None:
        if (
            action.action_type
            == ActionType.TYPE
        ):
            if (
                not action.target
                or action.value is None
            ):
                raise RuntimeError(
                    "TYPE requires target and value."
                )

            self.surface.type_text(
                action.target,
                action.value,
            )

            return None

        if (
            action.action_type
            == ActionType.CLICK
        ):
            if not action.target:
                raise RuntimeError(
                    "CLICK requires target."
                )

            self.surface.click(
                action.target
            )

            return None

        if (
            action.action_type
            == ActionType.READ
        ):
            if not action.target:
                raise RuntimeError(
                    "READ requires target."
                )

            value = self.surface.read_text(
                action.target
            )

            print(
                f"\nREAD RESULT: {value}"
            )

            return None

        if (
            action.action_type
            == ActionType.COMPLETE
        ):
            return {
                "status": "success",
                "result": action.value,
            }

        if (
            action.action_type
            == ActionType.ESCALATE
        ):
            return {
                "status": "needs_human",
                "result": action.reason,
            }

        raise RuntimeError(
            f"Unsupported action: "
            f"{action.action_type}"
        )
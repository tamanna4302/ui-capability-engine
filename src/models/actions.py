from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    READ = "read"
    WAIT = "wait"
    COMPLETE = "complete"
    ESCALATE = "escalate"


class LocatorStrategy(str, Enum):
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    CSS = "css"
    TABLE_CELL = "table_cell"


class Locator(BaseModel):
    strategy: LocatorStrategy

    role: str | None = None
    name: str | None = None
    label: str | None = None
    text: str | None = None
    selector: str | None = None

    # Used by TABLE_CELL
    row_text: str | None = None
    column_header: str | None = None


class Target(BaseModel):
    primary: Locator
    fallbacks: list[Locator] = Field(
        default_factory=list
    )


class Action(BaseModel):
    action_type: ActionType
    target: Target | None = None

    value: str | None = None
    output_name: str | None = None

    reason: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
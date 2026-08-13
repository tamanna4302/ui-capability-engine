from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.models.actions import Target


class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"


class CapabilityInput(BaseModel):
    name: str
    type: ParameterType
    required: bool = True
    description: str | None = None


class CapabilityOutput(BaseModel):
    name: str
    type: ParameterType
    description: str | None = None


class StepType(str, Enum):
    TYPE = "type"
    CLICK = "click"
    EXTRACT = "extract"


class ValueSource(BaseModel):
    literal: str | None = None
    parameter: str | None = None


class CheckpointType(str, Enum):
    URL_CONTAINS = "url_contains"
    TEXT_VISIBLE = "text_visible"


class Checkpoint(BaseModel):
    type: CheckpointType
    value: str


class ArtifactStep(BaseModel):
    id: str
    step_type: StepType

    target: Target | None = None

    value: ValueSource | None = None

    output_name: str | None = None

    checkpoint: Checkpoint | None = None

    description: str | None = None


class BusinessOutcome(BaseModel):
    code: str
    description: str
    detection_text: str


class CapabilityArtifact(BaseModel):
    schema_version: str = "1.0"

    capability_name: str
    capability_version: str

    description: str

    target_app: str
    entry_point: str

    inputs: list[CapabilityInput]
    outputs: list[CapabilityOutput]

    steps: list[ArtifactStep]

    success_condition: Checkpoint

    business_outcomes: list[BusinessOutcome] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
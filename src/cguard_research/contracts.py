"""Strict proposal contracts; no executable expressions or arbitrary operations."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("reviewer", "reason", "rationale", check_fields=False)
    @classmethod
    def meaningful_text(cls, value, info):
        minimum = 2 if info.field_name == "reviewer" else 10
        if len(value.strip()) < minimum or any(ord(c) < 32 for c in value):
            raise ValueError("Text must be meaningful and contain no control characters")
        return value.strip()

class Plan(Contract):
    schema_version: Literal[1] = 1
    objective: Literal["Describe the synthetic cohort by exposure group"] = (
        "Describe the synthetic cohort by exposure group")
    population: Literal["all_valid_rows"] = "all_valid_rows"
    group_by: Literal["group"] = "group"
    continuous: list[Literal["age_years", "weight_kg", "lab_value"]] = Field(
        default_factory=lambda: ["age_years", "weight_kg", "lab_value"], min_length=1)
    outcome: Literal["outcome"] = "outcome"
    missing_policy: Literal["available_per_variable"] = "available_per_variable"
    duplicate_policy: Literal["reject_duplicate_participant_ids"] = "reject_duplicate_participant_ids"
    interpretation: Literal["descriptive_only"] = "descriptive_only"
    rationale: str = Field(default="Prespecified descriptive summaries; no causal or treatment claims.",
                           min_length=10, max_length=1000)
    seed: Literal[0] = 0

    @field_validator("schema_version", "seed", mode="before")
    @classmethod
    def integer_literals(cls, value):
        if type(value) is not int:
            raise ValueError("Version and seed must be integers, not booleans or floats")
        return value

    @model_validator(mode="after")
    def unique_variables(self):
        if len(self.continuous) != len(set(self.continuous)):
            raise ValueError("continuous variables must be unique")
        return self

class Approval(Contract):
    scope: Literal["plan", "release"]
    reviewer: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=10, max_length=1000)
    attestation: Literal["human", "simulation"]
    binding: str = Field(pattern=r"^[0-9a-f]{64}$")
    timestamp: str
    warning_acknowledgements: list[str] = Field(default_factory=list)

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Condition(BaseModel):
    """Recursive condition tree for protocol evaluation."""

    field: str | None = None
    op: Literal["==", "!=", "<", ">", "<=", ">=", "in"] | None = None
    value: Any = None
    all: list["Condition"] | None = None
    any: list["Condition"] | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "Condition":
        leaf = self.field is not None or self.op is not None or self.value is not None
        composite = self.all is not None or self.any is not None
        if leaf and composite:
            raise ValueError("Condition cannot mix leaf and composite fields")
        if leaf:
            if self.field is None or self.op is None:
                raise ValueError("Leaf condition requires field and op")
            if self.value is None and self.op != "in":
                raise ValueError("Leaf condition requires a value")
            return self
        if composite:
            if self.all is None and self.any is None:
                raise ValueError("Composite condition requires 'all' or 'any'")
            if self.all is not None and self.any is not None:
                raise ValueError("Composite condition cannot define both 'all' and 'any'")
            return self
        raise ValueError("Condition must define a leaf or composite condition")


class RedFlag(BaseModel):
    id: str
    description: str
    condition: Condition
    disposition: str


class DispositionRule(BaseModel):
    condition: Condition
    disposition: str


class Protocol(BaseModel):
    protocol_id: str
    symptom_category: str
    required_fields: list[str] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    disposition_rules: list[DispositionRule] = Field(default_factory=list)
    safety_netting: str | None = None


def evaluate(condition: Condition | dict[str, Any], facts: dict[str, Any]) -> bool:
    """Recursively evaluate a condition against a facts dictionary."""

    if isinstance(condition, dict):
        condition = Condition.model_validate(condition)

    if condition.all is not None:
        return all(evaluate(child, facts) for child in condition.all)

    if condition.any is not None:
        return any(evaluate(child, facts) for child in condition.any)

    assert condition.field is not None
    assert condition.op is not None

    actual = facts.get(condition.field)
    expected = condition.value

    if condition.op == "==":
        return actual == expected
    if condition.op == "!=":
        return actual != expected
    if condition.op == "<":
        return actual is not None and expected is not None and actual < expected
    if condition.op == ">":
        return actual is not None and expected is not None and actual > expected
    if condition.op == "<=":
        return actual is not None and expected is not None and actual <= expected
    if condition.op == ">=":
        return actual is not None and expected is not None and actual >= expected
    if condition.op == "in":
        return actual is not None and expected is not None and actual in expected

    raise ValueError(f"Unsupported operator: {condition.op}")


__all__ = [
    "Condition",
    "RedFlag",
    "DispositionRule",
    "Protocol",
    "evaluate",
]

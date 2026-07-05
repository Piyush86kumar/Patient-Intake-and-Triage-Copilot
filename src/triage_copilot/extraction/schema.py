from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedFacts(BaseModel):
    model_config = {"extra": "allow"}
    symptom_category: str
    duration_minutes: Optional[int] = None
    severity: Optional[str] = None
    associated_symptoms: list[str] = Field(default_factory=list)
    explicit_negatives: list[str] = Field(default_factory=list)
    history_flags: list[str] = Field(default_factory=list)
    raw_text: str


__all__ = ["ExtractedFacts"]

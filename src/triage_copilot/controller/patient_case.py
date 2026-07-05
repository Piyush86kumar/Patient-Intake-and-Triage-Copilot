from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any

from triage_copilot.config import BASE_DIR
from triage_copilot.extraction.schema import ExtractedFacts


DB_PATH = BASE_DIR / "data" / "patient_cases.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class CaseStatus(str, Enum):
    GATHERING = "GATHERING"
    EMERGENCY = "EMERGENCY"
    DISPOSITION_GIVEN = "DISPOSITION_GIVEN"


class PatientCase:
    def __init__(
        self,
        conversation_id: str,
        facts: ExtractedFacts,
        matched_protocol_id: str | None = None,
        questions_asked: list[str] | None = None,
        disposition: str | None = None,
        status: CaseStatus = CaseStatus.GATHERING,
        turn_count: int = 0,
    ) -> None:
        self.conversation_id = conversation_id
        self.facts = facts
        self.matched_protocol_id = matched_protocol_id
        self.questions_asked = questions_asked or []
        self.disposition = disposition
        self.status = status
        self.turn_count = turn_count

    @classmethod
    def new(cls, conversation_id: str) -> "PatientCase":
        return cls(conversation_id=conversation_id, facts=ExtractedFacts(symptom_category="", raw_text=""))

    @staticmethod
    def _connection() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def _ensure_table(cls) -> None:
        with cls._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patient_cases (
                    conversation_id TEXT PRIMARY KEY,
                    facts TEXT NOT NULL,
                    matched_protocol_id TEXT,
                    questions_asked TEXT NOT NULL,
                    disposition TEXT,
                    status TEXT NOT NULL,
                    turn_count INTEGER NOT NULL
                )
                """
            )

    def save(self) -> None:
        self._ensure_table()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO patient_cases (
                    conversation_id,
                    facts,
                    matched_protocol_id,
                    questions_asked,
                    disposition,
                    status,
                    turn_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    facts=excluded.facts,
                    matched_protocol_id=excluded.matched_protocol_id,
                    questions_asked=excluded.questions_asked,
                    disposition=excluded.disposition,
                    status=excluded.status,
                    turn_count=excluded.turn_count
                """,
                (
                    self.conversation_id,
                    self.facts.model_dump_json(),
                    self.matched_protocol_id,
                    ",".join(self.questions_asked),
                    self.disposition,
                    self.status.value,
                    self.turn_count,
                ),
            )

    @classmethod
    def load(cls, conversation_id: str) -> "PatientCase" | None:
        cls._ensure_table()
        with cls._connection() as conn:
            row = conn.execute(
                "SELECT * FROM patient_cases WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()

        if not row:
            return None

        return cls(
            conversation_id=row["conversation_id"],
            facts=ExtractedFacts.model_validate_json(row["facts"]),
            matched_protocol_id=row["matched_protocol_id"],
            questions_asked=row["questions_asked"].split(",") if row["questions_asked"] else [],
            disposition=row["disposition"],
            status=CaseStatus(row["status"]),
            turn_count=row["turn_count"],
        )


__all__ = ["PatientCase", "CaseStatus"]

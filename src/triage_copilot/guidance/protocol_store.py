from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from triage_copilot.guidance.schema import Protocol


BASE_DIR = Path(__file__).resolve().parents[2]
PROTOCOLS_DIR = BASE_DIR.parent / "protocols"


class ProtocolStore:
    def __init__(self, protocols_dir: Path | None = None) -> None:
        self.protocols_dir = protocols_dir or PROTOCOLS_DIR
        self.protocols = self._load_protocols()

    def _load_protocols(self) -> dict[str, Protocol]:
        if not self.protocols_dir.exists():
            raise RuntimeError(f"Protocols directory not found: {self.protocols_dir}")

        protocols: dict[str, Protocol] = {}
        for path in sorted(self.protocols_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}

            if not isinstance(payload, dict):
                raise RuntimeError(f"Protocol file '{path.name}' must define a mapping at the top level")

            protocol = Protocol.model_validate(payload)
            protocols[protocol.protocol_id] = protocol

        if not protocols:
            raise RuntimeError(f"No protocol files found in {self.protocols_dir}")

        return protocols

    def get_protocol(self, protocol_id: str) -> Protocol:
        try:
            return self.protocols[protocol_id]
        except KeyError as exc:
            raise KeyError(f"Unknown protocol id '{protocol_id}'") from exc

    def get_all_protocols(self) -> list[Protocol]:
        return list(self.protocols.values())


protocol_store = ProtocolStore()

__all__ = ["ProtocolStore", "protocol_store"]

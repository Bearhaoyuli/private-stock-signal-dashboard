from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import Snapshot


class LocalSnapshotStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Snapshot | None:
        if not self.path.exists():
            return None
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return Snapshot.model_validate(payload)

    def save(self, snapshot: Snapshot) -> None:
        self.path.write_text(
            snapshot.model_dump_json(indent=2),
            encoding="utf-8",
        )


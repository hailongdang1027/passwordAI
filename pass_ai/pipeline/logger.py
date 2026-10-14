import json
from datetime import datetime, timezone
from pathlib import Path


class PipelineLogger:
    """Small JSONL logger for diagnostics; does not log raw candidate secrets."""

    def __init__(self, path="output/pipeline.log.jsonl"):
        self.path = Path(path)

    def log(self, event: str, **metadata):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **metadata,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

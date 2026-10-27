"""Convert COROS MCP sport-record text into candidate memories.

This is deliberately read-only: persistence and automatic polling require their
own deletion, retry and authorization handling. Unknown response shapes fail
closed rather than silently losing activities.
"""
import json
import re
from datetime import datetime, timezone


class CorosResponseError(ValueError):
    """An unsupported or incomplete COROS response."""


def parse_sport_records(result: dict) -> list[dict]:
    if not isinstance(result, dict) or result.get("isError"):
        raise CorosResponseError("COROS returned an error or unsupported response")
    content = result.get("content")
    if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict) or content[0].get("type") != "text":
        raise CorosResponseError("COROS response must contain one text block")
    text = content[0].get("text")
    if not isinstance(text, str):
        raise CorosResponseError("COROS response text is missing")
    if text.startswith('"'):
        try:
            text = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise CorosResponseError("COROS response is not valid JSON text") from exc
    if not isinstance(text, str):
        raise CorosResponseError("COROS response text is invalid")
    header = re.search(r"\((\d+) records?\)", text)
    blocks = re.split(r"(?m)^\s*\d+\.\s+", text)[1:]
    if not header or int(header.group(1)) != len(blocks):
        raise CorosResponseError("COROS record count is missing or inconsistent")
    records = []
    seen = set()
    for block in blocks:
        title = block.splitlines()[0].strip()
        record_id = re.search(r"\bLabelId:\s*(\d+)\b", block)
        timestamp = re.search(r"\bstartTimestamp=(\d+)\b", block)
        sport_type = re.search(r"\bSportType:\s*(\d+)\b", block)
        if not title or not record_id or not timestamp or not sport_type:
            raise CorosResponseError("COROS record is missing a required field")
        source_id = record_id.group(1)
        if source_id in seen:
            raise CorosResponseError("COROS response contains duplicate identifiers")
        seen.add(source_id)
        try:
            occurred = datetime.fromtimestamp(int(timestamp.group(1)), tz=timezone.utc)
        except (ValueError, OverflowError, OSError) as exc:
            raise CorosResponseError("COROS record has an invalid timestamp") from exc
        records.append({"source": "coros", "source_id": source_id,
                        "occurred_at": occurred.isoformat(timespec="microseconds"),
                        "text": title, "sport_type": int(sport_type.group(1))})
    return records

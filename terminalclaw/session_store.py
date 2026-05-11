import json
import os
import time
from typing import Any, Dict, List, Optional


def append_entry(store_path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(store_path) or ".", exist_ok=True)
    with open(store_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_entries(store_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(store_path):
        return []

    entries = []
    with open(store_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def format_entry(
    command: str = "",
    model: str = "",
    tokens: int = 0,
    analysis: str = "",
    duration_ms: int = 0,
    error_count: int = 0,
    log_file: str = "",
    **extra,
) -> Dict[str, Any]:
    return {
        "timestamp": int(time.time()),
        "command": command,
        "model": model,
        "tokens_used": tokens,
        "analysis_summary": analysis[:500],
        "duration_ms": duration_ms,
        "error_count": error_count,
        "log_file": log_file,
        **extra,
    }


def get_entry_count(store_path: str) -> int:
    return len(read_entries(store_path))


def get_latest_entry(store_path: str) -> Optional[Dict[str, Any]]:
    entries = read_entries(store_path)
    return entries[-1] if entries else None


def get_openclaw_sessions(base_dir: str = "") -> List[Dict[str, Any]]:
    import glob

    search_path = base_dir or os.path.expanduser(
        os.path.join("~", ".openclaw", "agents", "**", "*.jsonl")
    )
    session_files = glob.glob(search_path, recursive=True)

    all_entries = []
    for filepath in session_files:
        entries = read_entries(filepath)
        for entry in entries:
            entry["_source_file"] = filepath
        all_entries.extend(entries)

    return sorted(all_entries, key=lambda e: e.get("timestamp", 0), reverse=True)

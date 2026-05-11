import os
import re
import time
from typing import Dict, Optional

from terminalclaw.config import LOG_DIR, LOG_FILE, MAX_LOG_SIZE_MB, ERROR_PATTERNS


def setup_log_dir(log_dir: str = "") -> str:
    path = log_dir or LOG_DIR
    os.makedirs(path, exist_ok=True)

    log_file = os.path.join(path, "live.log")
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write("")

    return log_file


def get_log_info(log_file: str = "") -> Dict:
    fpath = log_file or LOG_FILE
    if not os.path.exists(fpath):
        return {"exists": False, "size_bytes": 0, "size_human": "0 B", "lines": 0}

    size = os.path.getsize(fpath)
    lines = 0
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for _ in f:
                lines += 1
    except (OSError, UnicodeDecodeError):
        pass

    return {
        "exists": True,
        "size_bytes": size,
        "size_human": _format_size(size),
        "lines": lines,
    }


def _format_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes} {unit}"
        size_bytes //= 1024
    return f"{size_bytes} TB"


def rotate_log(log_file: str = "", max_mb: int = 0) -> bool:
    fpath = log_file or LOG_FILE
    threshold_mb = max_mb or MAX_LOG_SIZE_MB

    if not os.path.exists(fpath):
        return False

    size_mb = os.path.getsize(fpath) / (1024 * 1024)
    if size_mb < threshold_mb:
        return False

    timestamp = int(time.time())
    archive_path = f"{fpath}.{timestamp}.old"
    os.rename(fpath, archive_path)

    with open(fpath, "w") as f:
        f.write("")

    return True


def count_errors(log_file: str = "") -> int:
    fpath = log_file or LOG_FILE
    if not os.path.exists(fpath):
        return 0

    combined = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)
    count = 0
    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if combined.search(line):
                    count += 1
    except (OSError, UnicodeDecodeError):
        pass

    return count


def read_tail(log_file: str = "", lines: int = 100) -> str:
    fpath = log_file or LOG_FILE
    if not os.path.exists(fpath):
        return ""

    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return ""

    return "".join(all_lines[-lines:])


def read_grep(log_file: str = "", pattern: str = "ERROR", max_lines: int = 200) -> str:
    fpath = log_file or LOG_FILE
    if not os.path.exists(fpath):
        return ""

    matches = []
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if compiled.search(line):
                    matches.append(line)
                    if len(matches) >= max_lines:
                        break
    except (OSError, UnicodeDecodeError):
        pass

    return "".join(matches)


def get_log_summary(log_file: str = "") -> Dict:
    info = get_log_info(log_file)
    error_count = count_errors(log_file)

    return {
        **info,
        "error_count": error_count,
        "tail_preview": read_tail(log_file, lines=10),
    }

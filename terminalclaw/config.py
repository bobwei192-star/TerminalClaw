import os

LOG_DIR = os.environ.get("TCLAW_LOG_DIR", "/tmp/tclaw")
LOG_FILE = os.path.join(LOG_DIR, "live.log")
SESSION_NAME = os.environ.get("TCLAW_SESSION", "terminalclaw")
OLLAMA_MODEL = os.environ.get("TCLAW_MODEL", "terminalclaw")
MAX_LOG_SIZE_MB = int(os.environ.get("TCLAW_MAX_LOG_MB", "500"))

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_API_TAGS = f"{OLLAMA_BASE_URL}/api/tags"

OPENCLAW_CONFIG_DIR = os.path.expanduser("~/.openclaw")
OPENCLAW_CONFIG_FILE = os.path.join(OPENCLAW_CONFIG_DIR, "openclaw.json")
OPENCLAW_SESSIONS_GLOB = os.path.join(OPENCLAW_CONFIG_DIR, "agents", "**", "*.jsonl")

MONITOR_INTERVAL_SECONDS = int(os.environ.get("TCLAW_MONITOR_INTERVAL", "30"))

ANALYZE_DEFAULT_LINES = int(os.environ.get("TCLAW_ANALYZE_LINES", "100"))

CONTEXT_TOKENS = int(os.environ.get("TCLAW_CONTEXT_TOKENS", "8192"))
CONTEXT_WINDOW = int(os.environ.get("TCLAW_CONTEXT_WINDOW", "65536"))

ERROR_PATTERNS = [
    r"\bERROR\b",
    r"\bFATAL\b",
    r"\bEXCEPTION\b",
    r"\bCRITICAL\b",
    r"\bPANIC\b",
    r"\bSEVERE\b",
]

import shutil
import subprocess
import sys
from typing import Dict, List, Optional

import requests

from terminalclaw.config import OLLAMA_API_TAGS, OLLAMA_MODEL


def _which(command: str) -> Optional[str]:
    return shutil.which(command)


def check_tmux() -> bool:
    return _which("tmux") is not None


def check_openclaw() -> bool:
    return _which("openclaw") is not None


def check_ollama_cli() -> bool:
    return _which("ollama") is not None


def check_tee() -> bool:
    return _which("tee") is not None


def check_ollama_service(timeout: int = 5) -> bool:
    try:
        resp = requests.get(OLLAMA_API_TAGS, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def check_ollama_model(model_name: str = "") -> bool:
    name = model_name or OLLAMA_MODEL
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return name in result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_missing_dependencies() -> List[str]:
    missing = []
    for cmd, name in [
        ("tmux", "tmux"),
        ("openclaw", "openclaw"),
        ("ollama", "ollama"),
        ("tee", "tee"),
    ]:
        if _which(cmd) is None:
            missing.append(name)
    return missing


def get_install_hints() -> Dict[str, str]:
    return {
        "tmux": "sudo apt install tmux",
        "openclaw": "npm install -g openclaw@latest",
        "ollama": "curl -fsSL https://ollama.com/install.sh | sh",
        "tee": "（系统自带 coreutils）",
    }


def pull_model(model_name: str) -> bool:
    try:
        subprocess.run(
            ["ollama", "pull", model_name],
            check=True,
            timeout=600,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def create_model_from_modelfile(model_name: str, modelfile_path: str) -> bool:
    try:
        subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            check=True,
            timeout=120,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def run_checks(model_name: str = "") -> Dict:
    missing = get_missing_dependencies()
    ollama_running = check_ollama_service()
    model_ready = False
    if missing:
        ollama_running = False

    if ollama_running:
        model_ready = check_ollama_model(model_name)

    return {
        "all_deps_present": len(missing) == 0,
        "missing_deps": missing,
        "install_hints": {k: v for k, v in get_install_hints().items() if k in missing},
        "ollama_running": ollama_running,
        "ollama_model_ready": model_ready,
        "tmux_available": check_tmux(),
        "openclaw_available": check_openclaw(),
        "ollama_cli_available": check_ollama_cli(),
        "tee_available": check_tee(),
    }

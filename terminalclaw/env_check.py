import shutil
import subprocess
from typing import Dict, List, Optional

import requests

from terminalclaw.config import (
    TCLAW_LLM_MODE,
    OLLAMA_API_TAGS,
    OLLAMA_LOCAL_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)


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


def is_cloud_mode() -> bool:
    return TCLAW_LLM_MODE == "cloud"


def is_local_mode() -> bool:
    return TCLAW_LLM_MODE == "local"


def check_ollama_service(timeout: int = 5) -> bool:
    try:
        resp = requests.get(OLLAMA_API_TAGS, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def check_ollama_model(model_name: str = "") -> bool:
    name = model_name or OLLAMA_LOCAL_MODEL
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


def check_cloud_api() -> bool:
    if not DEEPSEEK_API_KEY:
        return False
    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_missing_dependencies() -> List[str]:
    missing = []
    always_required = [
        ("tmux", "tmux"),
        ("openclaw", "openclaw"),
        ("tee", "tee"),
    ]
    for cmd, name in always_required:
        if _which(cmd) is None:
            missing.append(name)

    if is_local_mode():
        if _which("ollama") is None:
            missing.append("ollama")

    return missing


def get_install_hints() -> Dict[str, str]:
    return {
        "tmux": "sudo apt install tmux",
        "openclaw": "npm install -g openclaw@latest",
        "ollama": "curl -fsSL https://ollama.com/install.sh | sh",
        "tee": "（系统自带 coreutils）",
    }


def run_checks() -> Dict:
    missing = get_missing_dependencies()
    mode = TCLAW_LLM_MODE

    result = {
        "mode": mode,
        "all_deps_present": len(missing) == 0,
        "missing_deps": missing,
        "install_hints": {k: v for k, v in get_install_hints().items() if k in missing},
        "tmux_available": check_tmux(),
        "openclaw_available": check_openclaw(),
        "tee_available": check_tee(),
    }

    if is_local_mode():
        ollama_running = check_ollama_service() if len(missing) == 0 else False
        model_ready = False
        if ollama_running:
            model_ready = check_ollama_model()
        result.update({
            "llm_provider": "Ollama (本地)",
            "ollama_available": check_ollama_cli(),
            "ollama_running": ollama_running,
            "ollama_model_ready": model_ready,
            "ollama_model": OLLAMA_LOCAL_MODEL,
        })
    else:
        api_ok = check_cloud_api() if len(missing) == 0 else False
        result.update({
            "llm_provider": f"DeepSeek (云端) — {DEEPSEEK_BASE_URL}",
            "cloud_api_key_configured": bool(DEEPSEEK_API_KEY),
            "cloud_api_ok": api_ok,
            "cloud_model": DEEPSEEK_MODEL,
        })

    return result


def get_llm_provider_name() -> str:
    if is_cloud_mode():
        return "deepseek"
    return "ollama"

import subprocess
import time
from typing import Dict, List, Optional

from terminalclaw.config import SESSION_NAME, LOG_FILE


def _run_tmux(args: list, timeout: int = 10) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["tmux"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        result = subprocess.CompletedProcess(
            args=["tmux"] + args,
            returncode=127,
            stdout="",
            stderr="tmux: command not found",
        )
        return result


def session_exists(name: str = "") -> bool:
    session = name or SESSION_NAME
    result = _run_tmux(["has-session", "-t", session])
    return result.returncode == 0


def create_session(name: str = "") -> bool:
    session = name or SESSION_NAME
    if session_exists(session):
        return False

    _run_tmux(["new-session", "-d", "-s", session, "-n", "terminalclaw"])
    return session_exists(session)


def kill_session(name: str = "") -> bool:
    session = name or SESSION_NAME
    if not session_exists(session):
        return False

    _run_tmux(["kill-session", "-t", session])
    time.sleep(0.5)
    return not session_exists(session)


def rename_window(session: str, window_name: str) -> None:
    _run_tmux(["rename-window", "-t", f"{session}:1", window_name])


def set_pane_title(session: str, pane: str, title: str) -> None:
    _run_tmux(["select-pane", "-t", f"{session}:{pane}", "-T", title])


def split_pane(session: str, direction: str = "h") -> Optional[str]:
    flag = "-h" if direction == "h" else "-v"
    result = _run_tmux(["split-window", flag, "-t", f"{session}:1"])
    if result.returncode != 0:
        return None

    pane_result = _run_tmux(["display-message", "-p", "#{pane_index}"])
    return pane_result.stdout.strip()


def send_keys(session: str, pane: str, keys: str, enter: bool = True) -> bool:
    args = ["send-keys", "-t", f"{session}:{pane}"]
    if enter:
        args.extend(["-l", keys])
        result = _run_tmux(args)
    else:
        result = _run_tmux(args + [keys])
    return result.returncode == 0


def send_command(session: str, pane: str, command: str) -> bool:
    escaped = command.replace("'", "'\\''")
    full = f"'{escaped}' C-m"
    result = _run_tmux(["send-keys", "-t", f"{session}:{pane}", full])
    return result.returncode == 0


def attach_session(name: str = "") -> bool:
    session = name or SESSION_NAME
    if not session_exists(session):
        return False

    result = _run_tmux(["attach-session", "-t", session], timeout=0)
    return True


def list_panes(session: str = "") -> List[Dict]:
    sess = session or SESSION_NAME
    if not session_exists(sess):
        return []

    result = _run_tmux(
        ["list-panes", "-t", sess, "-F", "#{pane_index}|#{pane_title}|#{pane_pid}"]
    )
    if result.returncode != 0:
        return []

    panes = []
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|", 2)
            panes.append(
                {
                    "index": parts[0],
                    "title": parts[1] if len(parts) > 1 else "",
                    "pid": parts[2] if len(parts) > 2 else "",
                }
            )
    return panes


def launch_workspace(session: str = "") -> Dict:
    sess = session or SESSION_NAME

    if session_exists(sess):
        return {"ok": False, "error": f"会话 {sess} 已存在"}

    if not create_session(sess):
        return {"ok": False, "error": "无法创建 Tmux 会话"}

    rename_window(sess, "TerminalClaw")
    set_pane_title(sess, "1.1", "📋 日志输出")

    right_pane = split_pane(sess, "h")
    if right_pane:
        set_pane_title(sess, f"1.{right_pane}", "🤖 OpenClaw AI")
    else:
        kill_session(sess)
        return {"ok": False, "error": "无法创建右侧面板"}

    return {
        "ok": True,
        "session": sess,
        "left_pane": "1.1",
        "right_pane": f"1.{right_pane}",
    }


def init_log_pane(session: str, pane: str, log_command: str) -> None:
    log_dir = "/tmp/tclaw"
    log_file = f"{log_dir}/live.log"

    send_keys(session, pane, f"mkdir -p {log_dir}")

    banner = [
        f"echo '=== TerminalClaw 日志监控启动 ==='",
        f"echo '日志文件: {log_file}'",
        f"echo '按 Ctrl+C 停止日志，Ctrl+B D 离开会话'",
        f"echo ''",
    ]
    for cmd in banner:
        send_keys(session, pane, cmd)

    full_cmd = f"eval \"{log_command}\" 2>&1 | tee -a {log_file}"
    send_keys(session, pane, full_cmd)


def init_ai_pane(session: str, pane: str) -> None:
    banner = [
        f"echo '=== TerminalClaw AI 分析面板 ==='",
        f"echo ''",
        f"echo '可用指令:'",
        f"echo '  分析最近50行日志'",
        f"echo '  检查有没有错误'",
        f"echo '  分析输出中的异常模式'",
        f"echo ''",
    ]
    for cmd in banner:
        send_keys(session, pane, cmd)

    prompt = (
        f"openclaw agent --local --agent terminalclaw "
        f"-m '你是日志分析专家，日志文件在 {LOG_FILE}。"
        f"用户会用自然语言发出分析指令，你要优先用 read 工具读取日志文件，"
        f"必要时使用 exec grep/awk 进行复杂文本处理。'"
    )
    send_keys(session, pane, prompt)

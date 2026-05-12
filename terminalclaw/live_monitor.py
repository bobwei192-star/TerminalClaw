#!/usr/bin/env python3
"""
TerminalClaw Live Monitor — 右面板实时日志分析守护进程

工作方式:
  1. 打开 /tmp/tclaw/live.log，记录初始位置
  2. 每 N 秒检查文件是否有新内容
  3. 新行中出现 ERROR/FATAL/EXCEPTION 时，先即时回显再异步调用 openclaw agent 分析
  4. 分析结果实时输出到终端（右面板）
"""

import os
import re
import sys
import time
from datetime import datetime

import requests

LOG_FILE = os.environ.get("TCLAW_LOG_FILE", "/tmp/tclaw/live.log")
LOG_DIR = os.path.dirname(LOG_FILE)
POLL_INTERVAL = float(os.environ.get("TCLAW_POLL_INTERVAL", "3"))
MAX_LINES_PER_ANALYSIS = int(os.environ.get("TCLAW_MAX_ANALYSIS_LINES", "50"))
COOLDOWN_SECONDS = int(os.environ.get("TCLAW_COOLDOWN_SECONDS", "10"))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_TIMEOUT = int(os.environ.get("TCLAW_LLM_TIMEOUT", "25"))
DEEPSEEK_MAX_TOKENS = int(os.environ.get("TCLAW_LLM_MAX_TOKENS", "1024"))

ERROR_PATTERN = re.compile(
    r"\b(ERROR|FATAL|EXCEPTION|CRITICAL|PANIC|SEVERE|Traceback)\b",
    re.IGNORECASE,
)

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def print_banner():
    print(f"{BOLD}╔══════════════════════════════════════╗{NC}")
    print(f"{BOLD}║    TerminalClaw Live Monitor        ║{NC}")
    print(f"{BOLD}║    实时日志分析 · 自动错误检测      ║{NC}")
    print(f"{BOLD}╚══════════════════════════════════════╝{NC}")
    print()
    print(f"  日志文件: {LOG_FILE}")
    print(f"  扫描间隔: {POLL_INTERVAL}s | 冷却: {COOLDOWN_SECONDS}s")
    print()
    print(f"{CYAN}── {ts()} 监控启动 ──{NC}")
    print()


def read_new_lines(file_handle, last_position):
    file_handle.seek(last_position)
    new_content = file_handle.read()
    new_position = file_handle.tell()
    lines = new_content.split("\n") if new_content else []
    return lines, new_position


def has_errors(lines):
    for line in lines:
        if ERROR_PATTERN.search(line):
            return True
    return False


def extract_error_context(lines, max_lines=MAX_LINES_PER_ANALYSIS):
    error_lines = []
    for line in lines:
        if ERROR_PATTERN.search(line):
            error_lines.append(line.rstrip("\n").rstrip("\r"))
    return error_lines[-max_lines:]


def analyze_via_deepseek(error_lines):
    if not error_lines:
        return

    error_text = "\n".join(error_lines[-MAX_LINES_PER_ANALYSIS:])

    t_req_start = datetime.now()
    print(f"  {DIM}[{ts()}] → DeepSeek API ({DEEPSEEK_MODEL}, timeout={DEEPSEEK_TIMEOUT}s)...{NC}")

    try:
        resp = requests.post(
            f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是终端日志分析专家。简短、专业、只给结论。",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"最新日志错误，简洁分析（不重复原文）：\n\n```\n{error_text}\n```\n\n"
                            f"输出格式:\n"
                            f"【问题概要】<1句话>\n"
                            f"【可能根因】<1-2条>\n"
                            f"【建议命令】<1-2条>"
                        ),
                    },
                ],
                "max_tokens": DEEPSEEK_MAX_TOKENS,
                "temperature": 0.3,
            },
            timeout=DEEPSEEK_TIMEOUT,
        )

        t_resp = datetime.now()
        elapsed = (t_resp - t_req_start).total_seconds()

        if resp.status_code != 200:
            print(f"  {RED}[{ts()}] API {resp.status_code}: {resp.text[:200]}{NC}")
            return

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            print(f"  {YELLOW}[{ts()}] API 返回空 ({elapsed:.1f}s){NC}")
            return

        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        print(f"  {GREEN}[{ts()}] DeepSeek ({elapsed:.1f}s, {tokens_used} tokens){NC}")
        print(f"  {GREEN}{content}{NC}")

    except requests.Timeout:
        elapsed = (datetime.now() - t_req_start).total_seconds()
        print(f"  {YELLOW}[{ts()}] DeepSeek 超时 ({elapsed:.1f}s > {DEEPSEEK_TIMEOUT}s){NC}")
    except requests.ConnectionError:
        print(f"  {RED}[{ts()}] DeepSeek 连接失败{NC}")
    except Exception as e:
        print(f"  {RED}[{ts()}] 调用失败: {e}{NC}")


def main():
    print_banner()

    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("")

    last_pos = os.path.getsize(LOG_FILE)
    error_buffer = []
    last_analysis_time = 0
    scan_count = 0

    try:
        while True:
            t_loop_start = datetime.now()
            time.sleep(POLL_INTERVAL)
            scan_count += 1

            if not os.path.exists(LOG_FILE):
                continue

            t_file_check = datetime.now()
            current_size = os.path.getsize(LOG_FILE)

            if current_size < last_pos:
                last_pos = 0

            if current_size == last_pos:
                continue

            try:
                with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                    new_lines, last_pos = read_new_lines(f, last_pos)
            except (OSError, UnicodeDecodeError):
                continue

            if not new_lines:
                continue

            t_parse_done = datetime.now()

            new_error_lines = []
            for line in new_lines:
                if ERROR_PATTERN.search(line):
                    stripped = line.rstrip("\n").rstrip("\r")
                    error_buffer.append(stripped)
                    new_error_lines.append(stripped)

            t_filter_done = datetime.now()

            if not new_error_lines:
                continue

            print(f"{BLUE}[{ts()}] 扫描检测到 {len(new_error_lines)} 条新错误 (共缓冲 {len(error_buffer)} 条){NC}")

            now = time.time()
            if now - last_analysis_time > COOLDOWN_SECONDS:
                lines_to_analyze = error_buffer[-MAX_LINES_PER_ANALYSIS:]

                print(f"{RED}[{ts()}] 触发分析 — {len(lines_to_analyze)} 条错误{NC}")
                for eline in lines_to_analyze:
                    print(f"  {RED}▸ {eline[:120]}{NC}")

                t_analysis_start = datetime.now()
                file_delay = (t_file_check - t_loop_start).total_seconds()
                filter_delay = (t_filter_done - t_parse_done).total_seconds()
                print(f"  {DIM}[{ts()}] 耗时: 文件读={file_delay:.1f}s 过滤={filter_delay:.3f}s{NC}")

                analyze_via_deepseek(lines_to_analyze)

                t_analysis_end = datetime.now()
                total = (t_analysis_end - t_analysis_start).total_seconds()
                print(f"{CYAN}── [{ts()}] 本轮完成 ({total:.1f}s) ──{NC}")
                print()

                error_buffer = []
                last_analysis_time = now
            else:
                cooldown_left = COOLDOWN_SECONDS - (now - last_analysis_time)
                print(f"  {DIM}[{ts()}] 冷却中 ({cooldown_left:.0f}s)，暂不分析{NC}")

    except KeyboardInterrupt:
        print(f"\n{GREEN}[{ts()}] TerminalClaw Live Monitor 已停止{NC}")


if __name__ == "__main__":
    main()

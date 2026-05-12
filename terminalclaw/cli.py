#!/usr/bin/env python3
"""
TerminalClaw CLI — 统一命令行入口 (Click 框架)

支持两种 LLM 模式:
  local (默认) — 本地 Ollama + qwen3.5
  cloud        — 云端 DeepSeek API（或其他 OpenAI 兼容 API）
"""

import os
import sys
import time

import click

from terminalclaw.config import (
    TCLAW_LLM_MODE,
    LOG_FILE,
    LOG_DIR,
    SESSION_NAME,
    MONITOR_INTERVAL_SECONDS,
    ANALYZE_DEFAULT_LINES,
    OLLAMA_LOCAL_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
)
from terminalclaw.env_check import (
    run_checks,
    is_cloud_mode,
    is_local_mode,
)
from terminalclaw.log_manager import (
    setup_log_dir,
    get_log_summary,
    rotate_log,
    count_errors,
    read_tail,
    read_grep,
)
from terminalclaw.tmux_manager import (
    session_exists,
    launch_workspace,
    init_log_pane,
    init_ai_pane,
    kill_session,
    attach_session,
    list_panes,
)
from terminalclaw.session_store import (
    append_entry,
    format_entry,
)

ANSI_GREEN = "\033[0;32m"
ANSI_YELLOW = "\033[1;33m"
ANSI_RED = "\033[0;31m"
ANSI_CYAN = "\033[0;36m"
ANSI_NC = "\033[0m"


def _info(msg: str):
    click.echo(f"{ANSI_GREEN}[INFO]{ANSI_NC} {msg}")


def _warn(msg: str):
    click.echo(f"{ANSI_YELLOW}[WARN]{ANSI_NC} {msg}")


def _error(msg: str):
    click.echo(f"{ANSI_RED}[ERROR]{ANSI_NC} {msg}", err=True)


def _get_model_name() -> str:
    if is_cloud_mode():
        return DEEPSEEK_MODEL
    return OLLAMA_LOCAL_MODEL


@click.group()
@click.version_option(version="0.1.0", prog_name="tclaw")
def cli():
    """
    TerminalClaw — 终端日志 AI 分析工作流

    Tmux + OpenClaw + LLM 全本地方案

    模式切换: TCLAW_LLM_MODE=local (默认, 本地 Ollama)
              TCLAW_LLM_MODE=cloud (云端 DeepSeek API)
    """
    pass


@cli.command()
@click.argument("log_command", required=True)
def start(log_command):
    """启动双面板工作区（左日志 / 右 AI）"""
    mode_label = "云端 DeepSeek" if is_cloud_mode() else "本地 Ollama"
    _info(f"TerminalClaw 环境自检 (LLM: {mode_label}) ...")

    checks = run_checks()

    if checks["missing_deps"]:
        _error(f"缺少依赖: {', '.join(checks['missing_deps'])}")
        for dep, hint in checks["install_hints"].items():
            click.echo(f"  {dep}: {hint}")
        sys.exit(1)

    if is_local_mode():
        if not checks.get("ollama_running"):
            _error("Ollama 服务未运行，请执行: ollama serve")
            sys.exit(1)
        if not checks.get("ollama_model_ready"):
            _warn(f"模型 {OLLAMA_LOCAL_MODEL} 未找到，请执行: ollama pull {OLLAMA_LOCAL_MODEL}")
            sys.exit(1)
    else:
        if not checks.get("cloud_api_key_configured"):
            _error("DEEPSEEK_API_KEY 环境变量未设置")
            click.echo("  export DEEPSEEK_API_KEY=sk-xxxxxxxx")
            sys.exit(1)
        if not checks.get("cloud_api_ok"):
            _warn("DeepSeek API 连接失败，请检查 API Key 和网络")
            sys.exit(1)
        _info(f"DeepSeek API 连接正常 (模型: {DEEPSEEK_MODEL})")

    _info("环境检查通过")

    _info("初始化日志目录 ...")
    setup_log_dir()

    if session_exists():
        _warn(f"会话 {SESSION_NAME} 已存在")
        click.echo(f"  tclaw attach    # 接入已有会话")
        click.echo(f"  tclaw stop      # 停止并重建")
        sys.exit(1)

    _info("创建 Tmux 工作区 ...")
    result = launch_workspace()
    if not result["ok"]:
        _error(result["error"])
        sys.exit(1)

    _info("初始化左面板（日志输出）...")
    init_log_pane(result["session"], result["left_pane"], log_command)

    _info("初始化右面板（AI 分析）...")
    init_ai_pane(result["session"], result["right_pane"])

    _info("接入工作区 ...")
    attach_session()
    _info("工作区已退出")


@cli.command()
def attach():
    """接入已有工作区"""
    if not session_exists():
        _error(f"会话 {SESSION_NAME} 不存在")
        click.echo("使用 'tclaw start <命令>' 创建新会话")
        sys.exit(1)

    attach_session()


@cli.command()
def stop():
    """停止工作区"""
    if not session_exists():
        _warn(f"会话 {SESSION_NAME} 不存在")
        return

    kill_session()
    _info(f"会话 {SESSION_NAME} 已停止")


@cli.command()
@click.argument("lines", required=False, default=ANALYZE_DEFAULT_LINES)
def analyze(lines):
    """分析最新 N 行日志（默认 100）"""
    setup_log_dir()

    summary = get_log_summary()
    if not summary["exists"] or summary["lines"] == 0:
        _error("日志文件不存在或为空")
        click.echo("请先运行 'tclaw start <命令>' 启动日志监控")
        sys.exit(1)

    _info(f"日志文件: {summary['lines']} 行, {summary['error_count']} 个错误")
    _info(f"最近 {lines} 行日志:")

    tail_content = read_tail(lines=lines)
    click.echo(ANSI_CYAN + tail_content[:2000] + ANSI_NC)

    entry = format_entry(
        command="analyze",
        model=_get_model_name(),
        tokens=0,
        analysis=f"读取最近 {lines} 行日志",
        error_count=summary["error_count"],
        log_file=LOG_FILE,
    )
    store = os.path.join(LOG_DIR, "sessions.jsonl")
    append_entry(store, entry)

    _info("分析记录已保存")


@cli.command()
def live():
    """右面板实时监控 — Attach 模式"""
    from terminalclaw.live_monitor import main
    _info("启动 Live Monitor (Attach 模式) ...")
    main()


@cli.command()
def monitor():
    """后台监控模式（自动检测异常）"""
    _info("启动后台监控模式 ...")
    _info(f"每 {MONITOR_INTERVAL_SECONDS} 秒扫描一次")

    setup_log_dir()

    try:
        while True:
            did_rotate = rotate_log()
            if did_rotate:
                _warn("日志文件已轮转")

            err_count = count_errors()
            if err_count > 0:
                _warn(f"检测到 {err_count} 个错误/异常")
                grep_content = read_grep(pattern="ERROR|FATAL|EXCEPTION", max_lines=20)
                click.echo(ANSI_RED + grep_content[:1000] + ANSI_NC)

                entry = format_entry(
                    command="monitor",
                    model=_get_model_name(),
                    tokens=0,
                    analysis=f"自动检测到 {err_count} 个错误",
                    error_count=err_count,
                    log_file=LOG_FILE,
                )
                store = os.path.join(LOG_DIR, "sessions.jsonl")
                append_entry(store, entry)

            time.sleep(MONITOR_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        _info("监控已停止")


@cli.command()
def status():
    """查看状态"""
    click.echo("=== TerminalClaw 状态 ===")
    click.echo()

    if session_exists():
        click.echo(f"Tmux 会话: {ANSI_GREEN}运行中{ANSI_NC} ({SESSION_NAME})")
        panes = list_panes()
        for p in panes:
            click.echo(f"  面板 {p['index']}: {p['title']}")
    else:
        click.echo(f"Tmux 会话: {ANSI_RED}未运行{ANSI_NC}")

    click.echo()
    summary = get_log_summary()
    if summary["exists"]:
        click.echo(f"日志文件: {LOG_FILE}")
        click.echo(f"  大小: {summary['size_human']}")
        click.echo(f"  行数: {summary['lines']}")
        click.echo(f"  错误数: {summary['error_count']}")
    else:
        click.echo("日志文件: 未创建")

    click.echo()
    checks = run_checks()

    if checks["mode"] == "local":
        if checks.get("ollama_running"):
            click.echo(f"LLM: {ANSI_GREEN}Ollama 运行中{ANSI_NC}")
            model_status = (
                f"{ANSI_GREEN}就绪{ANSI_NC}"
                if checks.get("ollama_model_ready")
                else f"{ANSI_YELLOW}未找到{ANSI_NC}"
            )
            click.echo(f"  模型: {model_status} ({checks.get('ollama_model', '')})")
        else:
            click.echo(f"LLM: {ANSI_RED}Ollama 未运行{ANSI_NC}")
    else:
        if checks.get("cloud_api_ok"):
            click.echo(f"LLM: {ANSI_GREEN}DeepSeek 连接正常{ANSI_NC}")
        elif checks.get("cloud_api_key_configured"):
            click.echo(f"LLM: {ANSI_YELLOW}DeepSeek API Key 已设置，但连接失败{ANSI_NC}")
        else:
            click.echo(f"LLM: {ANSI_RED}DeepSeek API Key 未设置{ANSI_NC}")
        click.echo(f"  模型: {checks.get('cloud_model', DEEPSEEK_MODEL)}")


@cli.command()
@click.option("--openclaw", is_flag=True, help="部署 OpenClaw 配置模板")
@click.option("--tmux", is_flag=True, help="部署 Tmux 配置")
@click.option("--mode", default=None,
              type=click.Choice(["local", "cloud"]),
              help="LLM 模式 (local=Ollama, cloud=DeepSeek)")
@click.option("--all", "deploy_all", is_flag=True, help="部署全部配置（默认）")
def setup(openclaw, tmux, mode, deploy_all):
    """一键部署配置文件到对应位置"""

    if not any([openclaw, tmux, deploy_all]):
        deploy_all = True

    import shutil
    import json

    active_mode = mode or TCLAW_LLM_MODE
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(package_dir, "config")

    openclaw_dest = os.path.expanduser("~/.openclaw/openclaw.json")
    tmux_dest = os.path.expanduser("~/.tmux.conf")

    if deploy_all or openclaw:
        if active_mode == "cloud":
            model_primary = "deepseek/deepseek-chat"
        else:
            model_primary = "ollama/qwen3.5"

        _info(f"LLM 模式: {active_mode} → {model_primary}")
        click.echo()
        _info("为避免与 OpenClaw 原生配置冲突，TerminalClaw 不直接写入 ~/.openclaw/openclaw.json。")
        click.echo()
        click.echo("  请手动执行以下步骤:")
        click.echo()
        if active_mode == "cloud":
            click.echo(f"  1. 设置 DeepSeek API Key (环境变量):")
            click.echo(f"     export DEEPSEEK_API_KEY=sk-xxxxxxxx")
            click.echo()
            click.echo(f"  2. 配置 OpenClaw 使用 DeepSeek:")
            click.echo(f"     openclaw config set model primary {model_primary}")
            click.echo(f"     openclaw config set model fallback {model_primary}")
            click.echo()
            click.echo(f"  3. 添加 DeepSeek Provider (手动写入 ~/.openclaw/openclaw.json)")
            click.echo(f'     在 "providers" 中添加:')
            click.echo(f'     "deepseek": {{"baseUrl": "https://api.deepseek.com/v1", "model": "deepseek-chat", "apiKey": "env:DEEPSEEK_API_KEY"}}')
        else:
            click.echo(f"  1. 启动 Ollama:")
            click.echo(f"     ollama serve &")
            click.echo(f"     ollama pull qwen3.5")
            click.echo()
            click.echo(f"  2. 配置 OpenClaw 使用 Ollama:")
            click.echo(f"     openclaw config set model primary {model_primary}")
            click.echo(f"     openclaw config set model fallback {model_primary}")
        click.echo()
        click.echo(f"  参考模板: {os.path.join(config_dir, 'openclaw.template.json')}")

    if deploy_all or tmux:
        src = os.path.join(config_dir, "tmux.conf")
        if os.path.exists(src):
            if os.path.exists(tmux_dest):
                _warn(f"~/.tmux.conf 已存在，跳过")
            else:
                shutil.copy(src, tmux_dest)
                _info(f"已部署: {tmux_dest}")

    click.echo()

    if active_mode == "cloud":
        _info("云模式部署完成。下一步:")
        click.echo("  export DEEPSEEK_API_KEY=sk-xxxxxxxx")
        click.echo("  tclaw status")
        click.echo("  tclaw start 'npm run dev'")
    else:
        _info("本地模式部署完成。下一步:")
        click.echo("  ollama serve &")
        click.echo("  ollama pull qwen3.5")
        click.echo("  tclaw status")
        click.echo("  tclaw start 'npm run dev'")

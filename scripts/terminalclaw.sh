#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "[ERROR] Python 未安装"
    exit 1
fi

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

COMMAND="${1:-help}"
shift 2>/dev/null || true
COMMAND_ARGS=("$@")

case "$COMMAND" in
    start)
        "$PYTHON" -m scripts.tclaw start "${COMMAND_ARGS[@]}"
        ;;
    attach|resume)
        "$PYTHON" -m scripts.tclaw attach
        ;;
    stop|kill)
        "$PYTHON" -m scripts.tclaw stop
        ;;
    analyze|check)
        LINES="${COMMAND_ARGS[0]:-100}"
        "$PYTHON" -m scripts.tclaw analyze "$LINES"
        ;;
    monitor|watch)
        "$PYTHON" -m scripts.tclaw monitor
        ;;
    status|info)
        "$PYTHON" -m scripts.tclaw status
        ;;
    help|--help|-h)
        cat << 'EOF'
TerminalClaw - 终端日志 AI 分析工作流

用法:
  tclaw start <命令>    启动双面板工作区（左日志/右AI）
  tclaw attach          接入已有工作区
  tclaw stop            停止工作区
  tclaw analyze [行数]  分析最新N行日志（默认100）
  tclaw monitor         后台监控模式（自动检测异常）
  tclaw status          查看状态
  tclaw help            显示帮助

示例:
  tclaw start 'npm run dev'
  tclaw start 'docker logs -f myapp'
  tclaw start 'journalctl -u nginx -f'
  tclaw analyze 200
  tclaw monitor &

环境变量:
  TCLAW_LOG_DIR      日志缓存路径 (默认 /tmp/tclaw)
  TCLAW_SESSION       Tmux 会话名 (默认 terminalclaw)
  TCLAW_MODEL         Ollama 模型名 (默认 terminalclaw)

许可证: MIT
EOF
        ;;
    *)
        log_error "未知命令: $COMMAND"
        bash "$0" help
        exit 1
        ;;
esac

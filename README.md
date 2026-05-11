# TerminalClaw

> 基于 Tmux + OpenClaw + Ollama 的完全免费、本地化的终端日志 AI 分析方案

## 一句话

左面板实时输出日志，右面板 OpenClaw Agent 就绪分析，一个 `tclaw start` 全搞定。

## 架构

```
┌─────────────────────┐  ┌──────────────────────┐
│   Pane 0 (Left)     │  │   Pane 1 (Right)     │
│   日志输出面板       │  │   OpenClaw AI 分析   │
│                     │  │                      │
│  npm run dev ──┐    │  │  openclaw agent      │
│  docker logs ──┤    │  │                      │
│         │       │    │  │  用户输入自然语言    │
│         │ tee   │    │  │       │              │
│         ▼       │    │  │       │ read / exec  │
│  live.log ──────┼────┼─────── 文件读取        │
└─────────────────────┘  └──────────────────────┘
```

## 快速开始

### 环境要求

- Linux (Ubuntu 22.04+) / macOS (12+) / Windows WSL2
- Node.js ≥ 20 | Python ≥ 3.8 | Tmux ≥ 3.3 | Ollama ≥ 0.3.0
- OpenClaw ≥ 2026.4.5 (非 Docker) 或 ≥ 2026.4.1 (Docker)

### 安装

```bash
pip install terminalclaw
# 或
npm install -g terminalclaw
```

### 使用

```bash
# 启动双面板工作区
tclaw start 'npm run dev'

# 监控 Docker 容器日志
tclaw start 'docker logs -f myapp'

# 接入已有工作区
tclaw attach

# 分析最近 200 行日志
tclaw analyze 200

# 后台自动监控（30 秒轮询）
tclaw monitor &

# 查看状态
tclaw status

# 停止工作区
tclaw stop
```

## 配置

### OpenClaw 配置

将 `config/openclaw.template.json` 复制到 `~/.openclaw/openclaw.json`，关键配置：

- `contextTokens: 8192` + `contextWindow: 65536` — 双重覆盖 Ollama 上下文溢出 Bug
- 工具白名单限定 `/tmp/tclaw/` 目录下的安全命令

### Ollama 模型

```bash
ollama create terminalclaw -f config/Modelfile.terminalclaw
```

模型参数：num_ctx 65536 | temperature 0.3 | top_p 0.9

### Tmux 配置

```bash
cp config/tmux.conf ~/.tmux.conf
```

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest tests/ -v

# 运行 CLI
python -m scripts.tclaw --help
```

## 项目结构

```
TerminalClaw/
├── terminalclaw/          # Python 核心包
│   ├── config.py          # 环境变量 + 常量
│   ├── env_check.py       # 环境检测 (tmux/openclaw/ollama)
│   ├── log_manager.py     # 日志读写/轮转/分析
│   ├── session_store.py   # .jsonl 会话记录
│   └── tmux_manager.py    # Tmux 会话管理
├── scripts/
│   ├── terminalclaw.sh    # Bash 编排入口
│   └── tclaw.py           # Python CLI (Click)
├── config/                # 配置模板
├── tests/                 # pytest 测试 (68 个)
├── docs/                  # 文档
├── 施工文档.md
└── 定型设计.md
```

## 许可证

MIT

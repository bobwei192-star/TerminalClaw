# TerminalClaw

> 基于 Tmux + OpenClaw + Ollama 的完全免费、本地化的终端日志 AI 分析方案

## 一句话

左面板实时输出日志，右面板 AI 就绪分析，一个 `tclaw start` 全搞定。

## 架构

```
┌─────────────────────┐  ┌──────────────────────┐
│   Pane 0 (Left)     │  │   Pane 1 (Right)     │
│   日志输出面板       │  │   AI 分析面板         │
│                     │  │                      │
│  npm run dev ──┐    │  │  Live Monitor       │
│  docker logs ──┤    │  │  + DeepSeek API     │
│         │       │    │  │                      │
│         │ tee   │    │  │  用户输入自然语言    │
│         ▼       │    │  │       │              │
│  live.log ──────┼────┼─────── 文件读取        │
└─────────────────────┘  └──────────────────────┘
```

## 核心特性

- **完全免费**：本地 Ollama 模型 + DeepSeek API 双引擎，零订阅费用
- **实时分析**：3-5 秒延迟的错误检测与 AI 分析
- **持久会话**：Tmux detach/attach，工作不中断
- **灵活配置**：支持自定义触发模式、监听模式、模型选择
- **跨平台**：Linux/macOS/WSL2 原生支持

## 快速开始

### 环境要求

- Linux (Ubuntu 22.04+) / macOS (12+) / Windows WSL2
- Node.js ≥ 20 | Python ≥ 3.8 | Tmux ≥ 3.3 | Ollama ≥ 0.3.0
- OpenClaw ≥ 2026.4.5 (非 Docker)

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

# 后台自动监控
tclaw monitor &

# 查看状态
tclaw status

# 停止工作区
tclaw stop
```

## 配置

### 环境变量

```bash
# 解释器模式: direct_api (快速) | openclaw_agent (完整工具链)
export TCLAW_INTERPRETER="direct_api"

# 监听模式: errors (仅错误) | all (全部输出)
export TCLAW_LISTEN_MODE="errors"

# 自定义触发模式
export TCLAW_TRIGGER_PATTERNS="ERROR|FATAL|EXCEPTION|not found|failed|denied|timeout"

# DeepSeek API Key (用于 direct_api 模式)
export DEEPSEEK_API_KEY="your-api-key"
```

### OpenClaw 配置

将 `config/openclaw.template.json` 复制到 `~/.openclaw/openclaw.json`。

### Ollama 模型

```bash
ollama create terminalclaw -f config/Modelfile.terminalclaw
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
│   ├── cli.py             # CLI 命令定义
│   ├── config.py          # 配置管理
│   ├── env_check.py       # 环境检测
│   ├── live_monitor.py    # 实时监控
│   ├── log_manager.py     # 日志管理
│   ├── session_store.py   # 会话存储
│   └── tmux_manager.py    # Tmux 管理
├── scripts/               # 辅助脚本
├── config/                # 配置模板
├── docs/                  # 文档
│   ├── design/            # 设计文档
│   ├── implementation/    # 实现文档
│   ├── usage/             # 使用文档
│   └── issues/            # 问题记录
├── tests/                 # 测试用例
└── README.md
```

## 许可证

MIT
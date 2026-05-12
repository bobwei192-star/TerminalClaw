TerminalClaw 施工文档
======================

## 一、项目结构

```
TerminalClaw/
├── bin/                    # 可执行命令入口
│   └── tclaw              # 主 CLI 入口
├── config/                 # 配置文件模板
│   ├── Modelfile.terminalclaw  # Ollama 模型配置
│   ├── openclaw.template.json  # OpenClaw 配置模板
│   └── tmux.conf          # Tmux 配置
├── docs/                  # 文档目录
├── scripts/               # 辅助脚本
│   ├── tclaw.py          # Python 主脚本
│   └── terminalclaw.sh   # Bash 主控脚本
├── terminalclaw/          # Python 包源码
│   ├── __init__.py
│   ├── cli.py            # CLI 命令定义
│   ├── config.py         # 配置管理
│   ├── env_check.py      # 环境检测
│   ├── live_monitor.py   # 实时监控
│   ├── log_manager.py    # 日志管理
│   ├── session_store.py  # 会话存储
│   └── tmux_manager.py   # Tmux 管理
├── tests/                # 测试用例
├── package.json          # npm 包配置
├── requirements.txt      # Python 依赖
├── requirements-dev.txt  # 开发依赖
└── setup.py             # Python 包安装配置
```

## 二、环境准备

### 2.1 依赖安装

```bash
# 安装系统依赖（Ubuntu/Debian）
sudo apt-get update && sudo apt-get install -y tmux

# 安装 Node.js（推荐 20.x）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 安装 OpenClaw
npm install -g openclaw

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2.2 模型准备

```bash
# 拉取 qwen3.5 模型
ollama pull qwen3.5

# 或创建自定义模型（推荐）
ollama create terminalclaw -f config/Modelfile.terminalclaw
```

### 2.3 OpenClaw 配置

```bash
# 初始化 OpenClaw 配置
openclaw init

# 使用模板配置
cp config/openclaw.template.json ~/.openclaw/openclaw.json
```

## 三、核心功能实现

### 3.1 Tmux 会话管理

**文件：** `terminalclaw/tmux_manager.py`

**核心函数：**

| 函数名 | 功能 | 参数 |
|--------|------|------|
| `session_exists(session)` | 检查会话是否存在 | session: 会话名称 |
| `create_session(session)` | 创建新会话 | session: 会话名称 |
| `split_pane(session)` | 垂直分屏 | session: 会话名称 |
| `send_keys(session, pane, keys)` | 向面板发送命令 | session, pane, keys |
| `init_log_pane(session, pane, command)` | 初始化左面板（日志输出） | session, pane, command |
| `init_ai_pane(session, pane)` | 初始化右面板（AI 分析） | session, pane |
| `launch_workspace(log_command)` | 启动完整工作空间 | log_command: 用户日志命令 |

### 3.2 Live Monitor 实时监控

**文件：** `terminalclaw/live_monitor.py`

**核心函数：**

| 函数名 | 功能 |
|--------|------|
| `start_monitor()` | 启动监控主循环 |
| `read_log_tail(lines=50)` | 读取日志文件末尾内容 |
| `detect_errors(log_content)` | 检测错误关键字 |
| `analyze_via_deepseek(error_lines)` | 通过 DeepSeek API 分析 |
| `analyze_via_openclaw(error_lines)` | 通过 OpenClaw Agent 分析 |

**监控循环流程：**

```
┌─────────────────────────────────────────────────────────┐
│                    Live Monitor 循环                    │
├─────────────────────────────────────────────────────────┤
│  1. 检查日志文件变化                                    │
│         │                                              │
│         ▼                                              │
│  2. 读取新增日志行                                      │
│         │                                              │
│         ▼                                              │
│  3. 匹配 TCLAW_TRIGGER_PATTERNS                        │
│         │                                              │
│         ├── 匹配成功 ──▶ 提取上下文 ──▶ 调用 LLM 分析   │
│         │                                              │
│         └── 无匹配 ──▶ 继续等待                        │
│                                                        │
│  4. 输出分析结果（带时间戳）                            │
│         │                                              │
│         ▼                                              │
│  5. 等待 3 秒后重复循环                                 │
└─────────────────────────────────────────────────────────┘
```

### 3.3 配置管理

**文件：** `terminalclaw/config.py`

**环境变量配置：**

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TCLAW_LOG_DIR` | `/tmp/tclaw` | 日志缓存目录 |
| `TCLAW_LOG_FILE` | `live.log` | 日志文件名 |
| `TCLAW_SESSION` | `terminalclaw` | Tmux 会话名 |
| `TCLAW_MODEL` | `terminalclaw` | Ollama 模型名 |
| `TCLAW_INTERPRETER` | `direct_api` | 解释器模式 (direct_api/openclaw_agent) |
| `TCLAW_LISTEN_MODE` | `errors` | 监听模式 (errors/all) |
| `TCLAW_TRIGGER_PATTERNS` | `ERROR\|FATAL\|EXCEPTION\|CRITICAL\|PANIC\|SEVERE\|Traceback` | 触发分析的正则模式 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型名 |
| `DEEPSEEK_TIMEOUT` | `30` | API 超时时间（秒） |

### 3.4 环境检测

**文件：** `terminalclaw/env_check.py`

**检测项：**

| 检测项 | 命令/路径 | 检测方法 |
|--------|----------|----------|
| Tmux | `tmux --version` | 检查命令是否存在 |
| OpenClaw | `openclaw --version` | 检查命令是否存在 |
| Ollama | `ollama --version` | 检查命令是否存在 |
| Ollama 服务 | `http://127.0.0.1:11434/api/tags` | HTTP 请求检测 |
| 模型就绪 | `ollama list` | 检查指定模型是否存在 |
| 日志目录 | `/tmp/tclaw` | 检查目录是否存在，不存在则创建 |

### 3.5 CLI 命令

**文件：** `terminalclaw/cli.py`

**命令列表：**

| 命令 | 功能 | 参数 |
|------|------|------|
| `tclaw start <command>` | 启动工作空间 | command: 日志命令 |
| `tclaw attach` | 接入已有会话 | 无 |
| `tclaw stop` | 停止工作空间 | 无 |
| `tclaw analyze [lines]` | 独立分析模式 | lines: 分析行数（默认 100） |
| `tclaw live` | 启动实时监控 | 无 |
| `tclaw status` | 查看状态 | 无 |
| `tclaw setup [--listen mode]` | 配置工具 | mode: errors/all |
| `tclaw help` | 帮助信息 | 无 |

## 四、部署与发布

### 4.1 开发环境

```bash
# 克隆项目
git clone https://github.com/bobwei192-star/TerminalClaw.git
cd TerminalClaw

# 安装依赖
pip install -e .
npm install

# 启动开发会话
npm run dev:ai
```

### 4.2 生产部署

```bash
# 全局安装
npm install -g terminalclaw

# 或通过 pip 安装
pip install terminalclaw

# 使用
tclaw start "npm run dev"
```

### 4.3 Docker 部署（备选）

> **注意**：由于 OpenClaw v2026.4.5 在 Docker 中存在 exec 静默失败的回归 Bug，建议使用 WSL2 或 Linux 裸机部署。

## 五、测试策略

### 5.1 单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_env_check.py
pytest tests/test_tmux_manager.py
```

### 5.2 集成测试

| 测试场景 | 步骤 | 预期结果 |
|----------|------|----------|
| 环境检测 | 执行 `tclaw status` | 显示 Tmux、OpenClaw、Ollama 状态 |
| 工作空间启动 | 执行 `tclaw start "echo test"` | 成功创建 Tmux 双面板 |
| 日志写入 | 在左面板输入命令 | 日志自动写入 /tmp/tclaw/live.log |
| 错误检测 | 输入 `echo "ERROR test"` | 右侧检测到错误并触发分析 |
| 会话持久化 | Ctrl+B D detach，再 `tclaw attach` | 会话状态完整恢复 |

## 六、代码规范

### 6.1 Python 规范

- 遵循 PEP 8 编码规范
- 使用 type hints 类型注解
- 函数和类使用 Google 风格注释
- 代码行长度不超过 120 字符

### 6.2 Shell 规范

- 使用 `set -euo pipefail` 启用严格模式
- 变量命名使用下划线分隔（`LOG_DIR`）
- 函数命名使用下划线分隔（`init_log_pane`）
- 注释清晰，说明复杂逻辑

### 6.3 Git 规范

- 提交信息遵循 Conventional Commits 格式
- 分支命名：`feature/xxx`、`fix/xxx`、`docs/xxx`
- PR 需通过所有测试才能合并

## 七、安全考虑

### 7.1 命令执行白名单

OpenClaw exec 工具限制为以下安全命令：
- 文件读取：`cat`, `tail`, `head`
- 文本搜索：`grep`, `awk`, `sed`
- JSON 处理：`jq`
- 目录限制：仅 `/tmp/tclaw/`

### 7.2 环境变量保护

- API Key 仅通过环境变量传递
- 不记录敏感信息到日志
- 配置文件权限设置为 600

### 7.3 网络安全

- 本地模型推理，数据不出本机
- API 调用仅通过 HTTPS
- 不向第三方发送日志内容
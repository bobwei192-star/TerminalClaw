TerminalClaw 用户手册
======================

## 一、快速开始

### 1.1 安装

```bash
# 安装依赖
pip install terminalclaw
npm install -g terminalclaw

# 或从源码安装
git clone https://github.com/bobwei192-star/TerminalClaw.git
cd TerminalClaw
pip install -e .
```

### 1.2 环境准备

```bash
# 安装系统依赖（Ubuntu/Debian）
sudo apt-get install -y tmux

# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen3.5
```

### 1.3 配置 API（可选）

```bash
# 设置 DeepSeek API Key（用于快速分析模式）
export DEEPSEEK_API_KEY="your-api-key"
```

## 二、基本使用

### 2.1 启动工作空间

```bash
# 启动基本工作空间（左面板运行命令，右面板 AI 分析）
tclaw start "npm run dev"

# 启动并指定日志命令
tclaw start "docker logs -f my-container"
tclaw start "kubectl logs -f deployment/my-app"
```

### 2.2 会话管理

```bash
# 接入已有会话
tclaw attach

# 停止会话
tclaw stop

# 查看状态
tclaw status
```

### 2.3 实时监控

```bash
# 启动实时监控（右面板）
tclaw live

# 停止监控（Ctrl+C）
```

### 2.4 独立分析

```bash
# 分析最近 100 行日志
tclaw analyze

# 分析指定行数
tclaw analyze 50
```

## 三、配置选项

### 3.1 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TCLAW_LOG_DIR` | `/tmp/tclaw` | 日志缓存目录 |
| `TCLAW_SESSION` | `terminalclaw` | Tmux 会话名 |
| `TCLAW_MODEL` | `terminalclaw` | Ollama 模型名 |
| `TCLAW_INTERPRETER` | `direct_api` | 解释器模式 |
| `TCLAW_LISTEN_MODE` | `errors` | 监听模式 |
| `TCLAW_TRIGGER_PATTERNS` | 见下文 | 触发分析的关键词 |
| `DEEPSEEK_API_KEY` | - | DeepSeek API Key |

### 3.2 解释器模式

```bash
# API 直连模式（默认，快速）
export TCLAW_INTERPRETER="direct_api"

# OpenClaw Agent 模式（完整工具链）
export TCLAW_INTERPRETER="openclaw_agent"
```

### 3.3 监听模式

```bash
# 只监听错误（默认）
export TCLAW_LISTEN_MODE="errors"

# 监听所有输出
export TCLAW_LISTEN_MODE="all"
```

### 3.4 自定义触发模式

```bash
# 默认触发模式
export TCLAW_TRIGGER_PATTERNS="ERROR|FATAL|EXCEPTION|CRITICAL|PANIC|SEVERE|Traceback"

# 自定义触发模式
export TCLAW_TRIGGER_PATTERNS="ERROR|FATAL|not found|failed|denied|timeout|refused"
```

## 四、高级功能

### 4.1 会话持久化

```bash
# 启动会话
tclaw start "npm run dev"

# 断开会话（保持后台运行）
# 按 Ctrl+B D

# 重新接入
tclaw attach
```

### 4.2 多会话管理

```bash
# 创建多个独立会话
TCLAW_SESSION="session1" tclaw start "npm run dev"
TCLAW_SESSION="session2" tclaw start "docker logs -f nginx"

# 接入指定会话
TCLAW_SESSION="session1" tclaw attach
```

### 4.3 配置文件

**OpenClaw 配置**：`~/.openclaw/openclaw.json`

```json
{
  "providers": {
    "ollama": {
      "model": "qwen3.5",
      "contextTokens": 8192,
      "contextWindow": 65536
    }
  },
  "tools": {
    "exec": {
      "enabled": true,
      "sandbox": true,
      "allowedCommands": ["cat", "tail", "grep", "awk", "sed", "jq"]
    },
    "read": {
      "enabled": true
    }
  },
  "memory": {
    "enabled": true,
    "storage": "local"
  }
}
```

## 五、快捷键

### 5.1 Tmux 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+B %` | 垂直分屏 |
| `Ctrl+B "` | 水平分屏 |
| `Ctrl+B <方向键>` | 切换面板 |
| `Ctrl+B D` | 断开会话 |
| `Ctrl+B X` | 关闭面板 |

### 5.2 TerminalClaw 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+C` | 停止 Live Monitor |
| `Ctrl+T` | 切换解释器模式（待实现） |

## 六、故障排除

### 6.1 常见问题

**Q: 右面板没有显示分析结果**

A: 检查以下事项：
1. 确保 `DEEPSEEK_API_KEY` 已正确设置
2. 检查日志文件是否有内容：`cat /tmp/tclaw/live.log`
3. 确保触发模式包含正确的关键词

**Q: OpenClaw 启动太慢**

A: 使用 API 直连模式：
```bash
export TCLAW_INTERPRETER="direct_api"
```

**Q: 左面板命令不写入日志**

A: 确保使用的是支持的终端环境（WSL2/Linux/macOS），并检查脚本命令是否正常运行。

**Q: 右面板无法输入**

A: Live Monitor 运行时会阻塞输入。按 `Ctrl+C` 停止监控后即可输入，重新启动用 `tclaw live`。

### 6.2 日志位置

- 应用日志：`/tmp/tclaw/live.log`
- OpenClaw 日志：`~/.openclaw/logs/`
- TerminalClaw 日志：`/tmp/tclaw/terminalclaw.log`

### 6.3 重置配置

```bash
# 重置 OpenClaw 配置
rm ~/.openclaw/openclaw.json
openclaw init

# 清空日志缓存
rm -rf /tmp/tclaw
```

## 七、FAQ

### 7.1 为什么需要 WSL2？

由于 OpenClaw 在 Windows 原生环境存在 `exec` 空输出的 Bug（自 v2026.2.15 起未修复），TerminalClaw 必须要求 WSL2 环境。

### 7.2 如何切换模型？

```bash
# 使用不同的 Ollama 模型
export TCLAW_MODEL="qwen3.5"
```

### 7.3 如何自定义系统提示词？

修改 OpenClaw 的 Agent 配置文件，或通过 `openclaw agent --agent terminalclaw -m "your prompt"` 指定。

### 7.4 是否支持离线使用？

是的，使用本地 Ollama 模型时完全离线运行。

## 八、命令参考

```bash
tclaw start <command>     # 启动工作空间
tclaw attach              # 接入会话
tclaw stop                # 停止会话
tclaw analyze [lines]     # 分析日志
tclaw live                # 启动实时监控
tclaw status              # 查看状态
tclaw setup [options]     # 配置工具
tclaw help                # 帮助信息
```
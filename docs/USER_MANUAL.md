TerminalClaw 用户手册
基于 定型设计.md v0.3.0 | 实现版本 v0.1.0

Table of Contents

一、环境要求
二、前置依赖部署（第一次使用必读）
  2.1 安装 Tmux
  2.2 安装 Ollama 并拉取模型
  2.3 安装 OpenClaw 并写入配置
  2.4 一键自检
三、安装 TerminalClaw
四、配置文件说明
  4.1 Tmux 配置
  4.2 Ollama Modelfile
  4.3 OpenClaw 配置模板（重要）
五、快速上手
六、命令参考
七、故障排除

一、环境要求

TerminalClaw 设计目标是在已部署 OpenClaw + Ollama 的环境中一键工作。以下为硬性前置条件：

组件	最低版本	检查命令	TerminalClaw 用途
Tmux	3.3+	tmux -V	分屏管理、会话持久化、面板命令注入
Ollama	0.3.0+	ollama --version	本地 LLM 推理服务
Ollama 模型	qwen3.5（或任意 8B+ 模型）	ollama list	Agent 日志分析的大脑
OpenClaw	2026.4.5+（非 Docker）/ 2026.4.1（Docker）	openclaw --version	AI Agent 框架，提供 read/exec 工具

TerminalClaw 自身只依赖 Python 3.8+ 和 click + requests 两个库（pip install 自动安装）。

二、前置依赖部署

TerminalClaw 假设你已经有一份可工作的 OpenClaw + Ollama 环境。如果你需要从零开始部署，以下步骤是完整的最小部署指南。

2.1 安装 Tmux

```bash
sudo apt install tmux
tmux -V
```

2.2 安装 Ollama 并拉取模型

```bash
curl -fsSL https://ollama.com/install.sh | sh

ollama pull qwen3.5

ollama list
```

2.3 安装 OpenClaw 并写入配置

这是关键步骤。你需要先安装 OpenClaw，然后把 TerminalClaw 提供的配置模板合并到 OpenClaw 的配置中。

第 1 步：安装 OpenClaw

```bash
npm install -g openclaw@latest

openclaw --version
```

第 2 步：创建 OpenClaw 工作配置

OpenClaw 的主配置文件是 ~/.openclaw/openclaw.json。如果你已经有这份文件，请跳过创建步骤，进入"第 3 步：合并配置"。

如果没有，运行 OpenClaw 的引导向导来初始化：

```bash
openclaw onboard --install-daemon
```

向导会引导你完成 Gateway 守护进程安装、工作区创建、渠道（Telegram/Slack 等）配置。对于 TerminalClaw 场景，渠道配置是可选的——Agent 在 Tmux 面板中以命令行方式运行，不需要消息渠道。

第 3 步：合并 TerminalClaw 的 Ollama Provider 配置

TerminalClaw 在 config/openclaw.template.json 中提供了一份模板。你需要把其中的关键配置合并到 ~/.openclaw/openclaw.json 中。

以下是需要合并到 openclaw.json 中的配置片段（不是完整替换）：

{
  "providers": {
    "ollama": {
      "baseUrl": "http://127.0.0.1:11434/v1",
      "model": "terminalclaw",
      "contextTokens": 8192,
      "contextWindow": 65536
    }
  },
  "model": {
    "primary": "ollama/qwen3.5",
    "fallback": "ollama/qwen3.5"
  },
  "tools": {
    "exec": {
      "enabled": true,
      "sandbox": true,
      "allowedCommands": [
        "cat /tmp/tclaw/*.log",
        "tail -n * /tmp/tclaw/*.log",
        "grep -i error /tmp/tclaw/*.log",
        "jq *",
        "awk *",
        "sed *"
      ]
    }
  },
  "memory": {
    "enabled": true,
    "storage": "local"
  },
  "telemetry": {
    "enabled": false
  }
}

配置要点说明（基于定型设计 §4.3.2）：

contextTokens: 8192 + contextWindow: 65536
  OpenClaw v2026.3.13+ 存在 Ollama 上下文窗口强制 265K 的已知 Bug。
  仅配置 contextWindow 不足以绕过该 Bug。必须同时设置 contextTokens
  （强制限制实际 token 数）和 contextWindow（声明模型能力上限），
  双重覆盖才能生效。

model.primary: "ollama/qwen3.5"
  如果你用 config/Modelfile.terminalclaw 创建了定制模型，
  可以改为 "ollama/terminalclaw"。推荐先用 qwen3.5 验证环境正常。

tools.exec.allowedCommands
  白名单限制 Agent 可执行的命令。操作目录限定在 /tmp/tclaw/，
  确保 Agent 不会读写项目代码或其他敏感文件。

2.4 一键自检

安装完上述三个组件后，运行 TerminalClaw 的自检确认一切就绪：

```bash
tclaw status
```

输出示例:

=== TerminalClaw 状态 ===

Tmux 会话: 未运行

日志文件: /tmp/tclaw/live.log
  大小: 0 B
  行数: 0
  错误数: 0

Ollama: 运行中
  模型: 就绪

如果 Ollama 显示"未运行"或模型显示"未找到"，回到 2.2 检查。

三、安装 TerminalClaw

```bash
cd /path/to/TerminalClaw

pip install -e .
```

安装完成后，tclaw 命令全局可用：

```bash
tclaw --help
```

可选：安装 Tmux 推荐配置（非必须，但提升体验）

```bash
cp config/tmux.conf ~/.tmux.conf
```

四、配置文件说明

TerminalClaw 的 config/ 目录提供三份模板文件。它们不需要放在项目目录中——你需要把它们部署到对应工具的配置位置。

4.1 Tmux 配置

文件: config/tmux.conf
部署位置: ~/.tmux.conf

配置要点:
  - mouse on              鼠标支持，点击切换面板
  - history-limit 50000   保留 5 万行历史，满足长时间调试
  - base-index 1          面板编号从 1 开始
  - prefix C-a            快捷键前缀改为 Ctrl+A（GNU Screen 习惯）
  - | 垂直分屏  - 水平分屏

部署后重载：tmux source-file ~/.tmux.conf

4.2 Ollama Modelfile

文件: config/Modelfile.terminalclaw
用途: 创建 TerminalClaw 专用模型

如果你希望 Agent 使用定制系统提示词以优化日志分析效果：

```bash
ollama create terminalclaw -f config/Modelfile.terminalclaw
```

创建后在 openclaw.json 中把 model.primary 改为 "ollama/terminalclaw"。

如果不创建专用模型，TerminalClaw 会使用 qwen3.5，效果同样可接受。

Modelfile 参数:
  - FROM qwen3.5          基础模型
  - num_ctx 65536         64K 上下文窗口
  - temperature 0.3       低温度 → 确定性输出，减少分析幻觉
  - top_p 0.9             保留适度灵活性
  - repeat_penalty 1.1    避免长分析中重复措辞

4.3 OpenClaw 配置模板

文件: config/openclaw.template.json
部署位置: 合并到 ~/.openclaw/openclaw.json（不要直接覆盖）

此文件是 TerminalClaw 对 OpenClaw 配置的全部要求。如果你已有 openclaw.json，
只需追加 §2.3 中的配置片段。如果你从零开始，可以直接复制此文件：

```bash
cp config/openclaw.template.json ~/.openclaw/openclaw.json
```

模板中 Ollama Provider 的 model 字段为 "terminalclaw"。如果你没有创建
专用模型（§4.2），请改为 "qwen3.5"。

五、快速上手

确认前置依赖就绪后，三个命令覆盖最常见的使用场景：

1. 启动工作区（适用场景：开发调试）

   tclaw start 'npm run dev'

   这会在 Tmux 中创建双面板：
     左面板 — 执行 npm run dev，输出显示在终端并写入 /tmp/tclaw/live.log
     右面板 — 启动 OpenClaw Agent，等待你的自然语言分析指令

2. 在右面板中发送分析指令

   分析最近50行日志
   检查有没有错误
   分析输出中的异常模式

   每一条指令都会被 OpenClaw Agent 理解，自动选择 read 工具读日志
   或 exec grep/awk 执行复杂搜索，然后流式返回分析结果。

3. 离开后重新接入

   按 Ctrl+B 再按 D → 断开（Session 后台保持，日志继续写入）
   回来时执行:

   tclaw attach

   面板状态完整还原，无需重新启动日志命令或 Agent。

4. 停止工作区

   tclaw stop

   日志文件保留在 /tmp/tclaw/ 供事后分析。

六、命令参考

tclaw start <日志命令>
  启动双面板工作区。执行顺序：环境自检 → 日志目录初始化
  → 创建 Tmux 会话 → 左面板启动日志命令 → 右面板启动 Agent。
  
  如果已存在同名 Tmux 会话，会提示先执行 tclaw stop 或 tclaw attach。

  日志命令示例:
    tclaw start 'npm run dev'
    tclaw start 'docker logs -f myapp'
    tclaw start 'journalctl -u nginx -f'
    tclaw start 'tail -f /var/log/syslog'

tclaw attach
  接入已有工作区。Tmux 会话名默认为 terminalclaw。

tclaw stop
  停止工作区。执行 tmux kill-session，日志文件保留不删除。

tclaw analyze [行数]
  独立分析模式。不需要启动完整 Tmux 会话，直接读取日志文件
  并显示最近 N 行（默认 100）。适用于日志已在运行但不想进入多面板界面。

tclaw monitor
  后台监控模式。每 30 秒扫描一次日志文件，自动计数 ERROR/FATAL/EXCEPTION
  行数，检测到异常时立即输出。不依赖 Tmux，可用 & 放入后台运行。

  退出: Ctrl+C

tclaw status
  查看当前状态：Tmux 会话是否在运行、日志文件大小和行数、
  Ollama 服务状态和模型就绪情况。

tclaw --help
  显示上述所有命令和简要说明。

七、故障排除

7.1 Ollama 连接失败

tclaw status 显示 "Ollama: 未运行"

ollama serve
curl http://127.0.0.1:11434/api/tags

7.2 模型未找到

tclaw status 显示模型 "未找到"

ollama list

# 如果没有 qwen3.5
ollama pull qwen3.5

# 如果创建了专用模型但名字不对
ollama list | grep terminalclaw

7.3 OpenClaw exec 返回空

非 Docker 部署:
  openclaw --version  # 确认 ≥ 2026.4.5

Docker 部署:
  openclaw --version  # 确认 = 2026.4.1（v2026.4.5 存在 Docker exec 静默失败回归）

7.4 OpenClaw 上下文窗口异常大

检查 ~/.openclaw/openclaw.json 是否同时配置了 contextTokens 和 contextWindow。
仅配置 contextWindow 不足以绕过 v2026.3.13+ 的 Ollama 上下文溢出 Bug。

正确配置:
  "contextTokens": 8192,
  "contextWindow": 65536

7.5 Tmux 面板无法创建

tmux kill-server         # 清理僵死会话
tmux new -s test          # 测试基础功能
tmux -V                   # 确认 ≥ 3.3

7.6 日志文件不更新

ls -la /tmp/tclaw/live.log

确认 tclaw start 中的日志命令包含 tee -a（append 模式）。
如果日志命令本身没有输出（如 npm run dev 先编译再启动），
等待命令产生输出后日志文件才会有内容。

7.7 Windows 用户在 WSL2 中运行

OpenClaw 在 Windows 原生环境存在 exec 空输出 Bug（v2026.2.15+ 未修复）。
TerminalClaw 必须在 WSL2 中运行。

wsl
cd /mnt/c/Users/Tong/Desktop/TerminalClaw
tclaw start 'npm run dev'

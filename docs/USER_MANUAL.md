TerminalClaw 用户手册
基于 定型设计.md v0.3.0 | 实现版本 v0.1.0

一、环境要求
二、选择 LLM 模式
三、前置依赖部署 — 本地 Ollama 模式
四、前置依赖部署 — 云端 DeepSeek 模式（推荐）
五、安装 TerminalClaw
六、配置文件说明
七、快速上手
八、命令参考
九、故障排除

一、环境要求

部署环境: WSL2 或 Linux 裸机（Ubuntu 22.04+ / Debian 12+）。
不支持 Docker（OpenClaw v2026.4.5 Docker exec 静默失败回归）。
不支持 Windows 原生 PowerShell（OpenClaw v2026.2.15+ Windows exec 空输出 Bug）。
macOS 为 Tier-2 支持。

硬性依赖（两种 LLM 模式共用）:

组件	最低版本	检查命令	用途
Tmux	3.3+	tmux -V	分屏管理、会话持久化、面板命令注入
OpenClaw	2026.4.5+	openclaw --version	AI Agent 框架，提供 read/exec 工具
Python	3.8+	python3 --version	TerminalClaw 自身运行环境

LLM 层的依赖取决于你选择的模式（见下一节）。

二、选择 LLM 模式

TerminalClaw 支持两种 LLM 后端。通过环境变量 TCLAW_LLM_MODE 切换：

模式	TCLAW_LLM_MODE	LLM 后端	额外依赖	成本
云端（推荐）	cloud	DeepSeek API	无（仅需 API Key）	按量付费，极低
本地	local	Ollama + qwen3.5	Ollama 服务 + 模型	完全免费

本文档 §三 覆盖本地模式部署，§四 覆盖云端模式部署。
根据你的使用场景选择其中一节即可。

三、前置依赖部署 — 本地 Ollama 模式

使用终端环境变量或在 ~/.bashrc 中添加:

export TCLAW_LLM_MODE=local

3.1 安装 Ollama 并拉取模型

curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5
ollama list

3.2 安装 OpenClaw

npm install -g openclaw@latest
openclaw --version

3.3 部署配置

tclaw setup --mode local

3.4 自检

ollama serve &
tclaw status

四、前置依赖部署 — 云端 DeepSeek 模式（推荐）

无需安装 Ollama，无需下载模型，无需磁盘空间。

4.1 设置 DeepSeek API Key

export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TCLAW_LLM_MODE=cloud

建议写入 ~/.bashrc 持久化。

4.2 安装 OpenClaw

npm install -g openclaw@latest
openclaw --version

4.3 部署配置

tclaw setup --mode cloud

这会自动写入 ~/.openclaw/openclaw.json，将 Provider 配置为 DeepSeek。

4.4 自检

tclaw status

预期输出:

=== TerminalClaw 状态 ===
Tmux 会话: 未运行
日志文件: 未创建
LLM: DeepSeek 连接正常
  模型: deepseek-chat

五、安装 TerminalClaw

cd /path/to/TerminalClaw
pip install -e .

安装完成后 tclaw 命令全局可用。

可选：安装 Tmux 推荐配置

cp config/tmux.conf ~/.tmux.conf

六、配置文件说明

TerminalClaw 的 config/ 目录提供三份模板。tclaw setup --mode <local|cloud>
自动完成部署。也可手动操作：

6.1 OpenClaw 配置（关键）

文件: config/openclaw.template.json
部署位置: ~/.openclaw/openclaw.json

此模板包含两个 Provider:

ollama — 本地模式，API 地址 127.0.0.1:11434/v1
deepseek — 云端模式，API 地址 api.deepseek.com/v1，API Key 从环境变量 DEEPSEEK_API_KEY 读取

tclaw setup --mode cloud 自动将 model.primary 改为 deepseek/deepseek-chat。
tclaw setup --mode local 自动将 model.primary 改为 ollama/qwen3.5。

关键配置: contextTokens: 8192 + contextWindow: 65536
  双重覆盖 Ollama 上下文溢出 Bug。仅配置 contextWindow 不足以绕过该 Bug。

exec 白名单: 限定 /tmp/tclaw/ 目录下的安全命令。
  确保 Agent 不会读写项目代码或其他敏感文件。

6.2 Tmux 配置

文件: config/tmux.conf | 部署: ~/.tmux.conf

mouse on             鼠标支持
history-limit 50000  5 万行历史
base-index 1         面板从 1 编号
prefix C-a           Ctrl+A 快捷键
| 垂直分屏  - 水平分屏

6.3 Ollama Modelfile（仅本地模式）

文件: config/Modelfile.terminalclaw
用途: 创建定制 Agent 系统提示词（可选，直接用 qwen3.5 效果同样可接受）

ollama create terminalclaw -f config/Modelfile.terminalclaw

七、快速上手

7.1 云模式（推荐 — 零本地依赖）

export DEEPSEEK_API_KEY=sk-xxxxxxxx
export TCLAW_LLM_MODE=cloud
tclaw start 'npm run dev'

7.2 本地模式

export TCLAW_LLM_MODE=local
ollama serve &
tclaw start 'npm run dev'

两种模式体验完全相同:
  左面板 → 执行日志命令，输出显示 + 写入 /tmp/tclaw/live.log
  右面板 → 启动 OpenClaw Agent，接受自然语言分析指令

7.3 在右面板中发送分析指令

分析最近50行日志
检查有没有错误
分析输出中的异常模式

7.4 离开后重新接入

Ctrl+B 再按 D → 断开（后台保持，日志继续写入）
回来时:

tclaw attach

7.5 停止

tclaw stop

八、命令参考

tclaw status
  查看当前状态: Tmux 会话、日志文件、LLM 连接。

tclaw start <日志命令>
  启动双面板工作区。自动环境自检 → 创建 Tmux 会话 → 左右面板初始化。

tclaw attach
  接入已有工作区。

tclaw stop
  停止工作区。日志文件保留。

tclaw analyze [行数]
  独立分析模式，直接读取日志文件并显示最近 N 行（默认 100）。

tclaw monitor
  后台监控，每 30 秒扫描异常并实时输出。

tclaw setup --mode <local|cloud>
  一键部署配置文件。

tclaw --help
  显示所有命令。

九、故障排除

9.1 DeepSeek API 连接失败

tclaw status → "DeepSeek API Key 未设置"

export DEEPSEEK_API_KEY=sk-xxxxxxxx

tclaw status → "API Key 已设置但连接失败"

curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
     https://api.deepseek.com/v1/models

9.2 Ollama 连接失败（本地模式）

ollama serve
curl http://127.0.0.1:11434/api/tags

9.3 模型未找到（本地模式）

ollama list
ollama pull qwen3.5

9.4 OpenClaw exec 返回空

openclaw --version  # 确认 ≥ 2026.4.5

9.5 OpenClaw 上下文窗口异常大

检查 ~/.openclaw/openclaw.json 是否同时配置了:
  "contextTokens": 8192,
  "contextWindow": 65536

9.6 Tmux 面板无法创建

tmux kill-server
tmux new -s test
tmux -V  # 确认 ≥ 3.3

9.7 日志文件不更新

ls -la /tmp/tclaw/live.log
# 确认 tclaw start 中的日志命令包含 tee -a

9.8 切换 LLM 模式

tclaw setup --mode cloud   # 切换到 DeepSeek
tclaw setup --mode local   # 切换到 Ollama

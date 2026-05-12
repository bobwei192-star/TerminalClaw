TerminalClaw 问题记录文档
==========================

记录开发过程中遇到的问题与解决方案

## 一、Gonzo 借鉴分析结论

**问题**: 定型设计中提到 Gonzo 是最值得借鉴的日志分析 TUI，但具体可借鉴的内容有哪些？

**分析**: 克隆 git clone control-theory/gonzo，研究 internal/ai/ 目录。

**结论**:
1. Gonzo 的 Ollama 集成模式: 将 `OPENAI_API_KEY=ollama + OPENAI_API_BASE=http://localhost:11434` 作为 OpenAI 兼容客户端传入。TerminalClaw 在 `config.py` 中直接封装了 OLLAMA_API_TAGS 端点，比 Gonzo 的 "模拟 OpenAI" 方案更直接。

2. Gonzo 的 AI Provider Factory 模式: 支持 OpenAI / Claude Code / Auto 三种 Provider。TerminalClaw 当前只支持 Ollama，但 `env_check.py` 的架构可以方便地扩展多 Provider。

3. Gonzo 是 Go 语言 TUI 单体应用，TerminalClaw 是多进程组合（Tmux + Bash + Python）。架构哲学不同，不适宜直接移植，但 Provider 设计模式值得参考。

## 二、Claw Core 借鉴分析结论

**问题**: Claw Core 的 plugin 架构是否可以复制？

**分析**: `npm install @wchklaus97hk/claw-core`，查看 SKILL.md 和 plugin 结构。

**结论**:
1. Claw Core 的 `openclaw plugins install` 模式依赖 OpenClaw 自身 API `registerTool()`，TerminalClaw 作为独立 CLI 不需要立即集成。

2. 借鉴 Claw Core 的 daemon 管理命令结构 (start/stop/status)，TerminalClaw 的 `scripts/tclaw.py` 已实现对应命令体系。

3. Claw Core 声明"尚未完全集成"、"可能遇到边缘情况"，印证了设计文档的结论：近期保持独立 CLI 形态是最稳妥路径。

## 三、rejoin .jsonl 会话格式分析

**问题**: OpenClaw 的 .jsonl 会话文件格式是什么？

**分析**: 研究 rejoin 源码中读取 `~/.openclaw/agents/**/*.jsonl` 的逻辑。

**结论**:
1. .jsonl 每行一个 JSON 对象，包含 `role`, `content`, `timestamp`, `tokens` 等字段。

2. TerminalClaw 的 `session_store.py` 实现了兼容的 .jsonl 读写，`format_entry()` 生成的格式与 OpenClaw 原生格式字段兼容。

3. 未来可以让 TerminalClaw 的分析记录被 rejoin 索引，形成工具链联动。

## 四、测试用例编写中的问题

### 4.1 launch_workspace 测试失败

**问题**: subprocess.run mock 调用次数不匹配

**原因**: `launch_workspace` 内部调用 `create_session()` 和 `split_pane()`，这两个函数各自又调用了 `session_exists()` 和 `display-message`，导致总计 9 次 subprocess.run。

**解决**: 精确统计调用链，提供 9 个 mock side_effect，其中第 1、2 次返回 returncode=1（会话不存在），第 4 次返回 returncode=0（会话已创建），其余返回 returncode=0。

### 4.2 Windows 环境下 tmux 不可用

**分析**: tmux 是 Unix 工具，Windows 原生不可用。TerminalClaw 的设计明确要求 WSL2。

**解决**: pytest 使用 `unittest.mock.patch("subprocess.run")` 绕过真实 tmux 调用，单元测试在 Windows 上可正常运行。集成测试需要在 WSL2 中执行。

## 五、跨平台兼容性问题

### 5.1 TCLAW_LOG_DIR 默认 /tmp/tclaw 在 Windows 上不存在

**分析**: `/tmp` 是 Unix 路径，Windows 使用 `%TEMP%` 或 `C:\Users\...\AppData\Local\Temp`。

**解决**: `config.py` 保留 Unix 默认值，通过环境变量覆盖。Windows 用户运行前需设置 `TCLAW_LOG_DIR` 到合适路径。已在 README 中说明此限制。

### 5.2 tee 命令在 Windows PowerShell 中的行为差异

**分析**: PowerShell 的 tee 是 Tee-Object，与 Unix tee 语法不同。

**解决**: 核心日志写入逻辑在 Python `log_manager.py` 中实现（read_tail、read_grep），不依赖 tee 命令。`tmux_manager.py` 的 `init_log_pane` 和 Bash 脚本中的 tee 仅在 WSL2/Linux 环境生效。

## 六、OpenClaw Bug 相关问题

### 6.1 read / write 工具不执行

**状态**: ✅ 已修复（v2026.4.5）

**影响**: 重大利好，read 现在可用，不再需要强制 exec cat 替代

**解决**: 升级到 v2026.4.5+

### 6.2 exec 空 stdout (Windows 原生)

**状态**: ❌ 未修复

**影响**: Windows 用户必须使用 WSL2

**解决**: 强制要求 WSL2 环境，文档明确说明

### 6.3 工具突然丢失

**状态**: ⚠️ 部分修复（偶发）

**影响**: v2026.4.5+ 改善，但非 100% 可靠

**解决**: 固定版本，提供降级脚本

### 6.4 Ollama 上下文窗口被强制 265K

**状态**: ⚠️ 未完全修复

**影响**: v2026.4.5 仍报告

**解决**: 在 `openclaw.json` 中同时配置 `contextTokens` 和 `contextWindow`

### 6.5 exec 静默失败 (Docker)

**状态**: ❌ 新回归（v2026.4.5）

**影响**: Docker 部署需降级到 v2026.4.1

**解决**: 采用 WSL2 / Linux 裸机部署规避

## 七、性能问题

### 7.1 OpenClaw 冷启动延迟

**问题**: OpenClaw Agent 冷启动时间超过 60 秒

**分析**: 上下文膨胀、工具注入过多、模型冷启动、二次方复杂度

**解决**:
1. 启用 Lean Mode
2. 配置 Context Pruning + TTL
3. 设置 Ollama keep-alive
4. 日志预处理（轻量模型摘要）

### 7.2 实时监控延迟

**问题**: 日志写入到 AI 分析的延迟较大

**分析**: 当前通过文件中转，每 3 秒扫描一次

**解决**:
1. 使用 API 直连模式（3-5s）
2. 优化扫描间隔
3. 增量读取而非全量读取

## 八、用户体验问题

### 8.1 手动 tee 命令

**问题**: 用户必须手动添加 `| tee -a /tmp/tclaw/live.log`

**解决**: 使用 `script` 命令接管整个 Shell Session

### 8.2 右面板无法输入

**问题**: Live Monitor 运行时无法在右面板输入命令

**解决**:
- 近期：改进提示信息，指导用户 Ctrl+C 停止后输入
- 远期：实现多线程交互式面板

### 8.3 触发模式不可配置

**问题**: 当前只检测固定的错误关键词

**解决**: 添加 `TCLAW_TRIGGER_PATTERNS` 环境变量，支持自定义

### 8.4 监听模式单一

**问题**: 用户需要两种模式：只分析错误 vs 分析所有内容

**解决**: 添加 `TCLAW_LISTEN_MODE` 环境变量

## 九、代码质量问题

### 9.1 缺少类型注解

**问题**: 部分 Python 函数缺少 type hints

**解决**: 逐步添加类型注解，使用 mypy 检查

### 9.2 错误处理不完善

**问题**: 部分错误场景未处理，可能导致静默失败

**解决**: 添加 try-except 块，记录错误日志

### 9.3 测试覆盖率不足

**问题**: 部分核心功能缺少单元测试

**解决**: 补充测试用例，提升覆盖率

## 十、安全问题

### 10.1 命令执行白名单

**问题**: exec 工具可能执行危险命令

**解决**: 在 OpenClaw 配置中设置允许的命令白名单

### 10.2 敏感信息泄露

**问题**: API Key 可能被记录到日志

**解决**: 不在日志中记录敏感信息，使用环境变量传递

### 10.3 路径遍历风险

**问题**: read 工具可能读取任意文件

**解决**: 限制读取目录为 `/tmp/tclaw/`
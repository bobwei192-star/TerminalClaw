TerminalClaw 实测问题诊断与改进方案
实测日期: 2026-05-12 | 状态: 待改代码

一、问题 1：左边用户必须手动 tee-a — 应自动化

1.1 现象

当前左面板的实际使用方式是：

  eval "npm run dev" 2>&1 | tee -a /tmp/tclaw/live.log

用户必须在命令末尾加 `| tee -a /tmp/tclaw/live.log`。如果用户直接敲 `ipconfig` 或 `docker ps`，
输出不会写入 live.log，右侧 Live Monitor 无法检测到任何内容。

1.2 根因

目前的 `init_log_pane()` 只是用 `send_keys` 把用户提供的日志命令包裹了一层 `eval "…" 2>&1 | tee -a …`
然后发到左面板。但左面板是一个普通的 Bash shell——用户可以在任何时候换行、
执行新命令。一旦切到别的命令（不是初始那条带 tee 的命令），新输出就丢失了。

本质问题是：**tee 是命令级的，不是 Shell 级的**。没有"这个 Shell 的所有输出自动 tee 到文件"的机制。

1.3 方案

方案 A (推荐): 用 `script` 命令接管整个 Shell Session

script 是 Linux 原生工具，可以记录一个终端会话的所有输入输出到文件。
左面板启动时不用交互式 Bash，而是启动一个 `script` 会话：

  script -q -f -a /tmp/tclaw/live.log -c "bash --rcfile <(echo 'PS1=...')"

效果：用户在左面板做的任何事情——`npm run dev`、`docker ps`、`ipconfig`、`cat error.log`——
全部自动写入 live.log，无需手动加 tee。

| 维度 | 方案 A (script) | 当前方案 (tee) |
|------|----------------|---------------|
| 全自动 | ✅ 所有输出自动记录 | ❌ 用户必须手动 tee |
| 透明性 | ✅ 用户无感知 | ❌ 用户必须记住管道语法 |
| 退出行为 | Ctrl+D 退出 script | Ctrl+C 停止当前命令 |
| 兼容性 | Linux/macOS 原生 | Linux/macOS 原生 |
| ANSI 颜色 | 原样保留（可过滤） | 原样保留 |

方案 B: 修改 Shell PROMPT_COMMAND 做每次命令后自动追加

在每个命令执行完后，自动把终端缓冲区内容追加到 live.log。
但这依赖于 $PROMPT_COMMAND 机制，复杂且不可靠。

结论：推荐方案 A。

二、问题 2：解释模式选择 — 部署时可选 OpenClaw Agent 或 LLM API 直连

2.1 现象

当前 `live_monitor.py` 已经切换到 DeepSeek API 直连（见 §4.3 的问题），
但代码中没有保留 OpenClaw Agent 的选项。如果用户想用 OpenClaw Agent（比如需要 read/exec 工具链、
需要多轮对话记忆），无法回退。

2.2 方案

在部署阶段提供两种解释模式，由环境变量 `TCLAW_INTERPRETER` 控制：

| 模式 | TCLAW_INTERPRETER | LLM 调用方式 | 延迟 | 工具链 | 推荐 |
|------|------------------|-------------|------|--------|------|
| API 直连 | `direct_api` (默认) | Python requests → DeepSeek | 3-5s | 无 | ✅ 截至 2026-05-12 推荐 |
| OpenClaw Agent | `openclaw_agent` | subprocess openclaw agent | 60s+ | read/exec/memory | 远期可用性改善后推荐 |

为什么默认推荐 `direct_api`：
- OpenClaw v2026.5.7 的 `openclaw agent --session-id` 冷启动约 60 秒
- DeepSeek API 直连 3-5 秒，满足"10 秒内"需求
- Live Monitor 场景不需要 Agent 的记忆/工具链——只需要一句话分析

实现方式：`live_monitor.py` 在启动时读取 `TCLAW_INTERPRETER`，
选择 `analyze_via_deepseek()` 或 `analyze_via_openclaw()`。

三、问题 3：右侧检测关键字应可配置

3.1 现象

当前 Live Monitor 只检测 ERROR/FATAL/EXCEPTION/CRITICAL/PANIC/SEVERE/Traceback 这 7 种模式。
用户输入 `ipconfig` 得到 "Command 'ipconfig' not found" — 这不是 ERROR 关键字，
但确实是用户关心的错误信息。

3.2 方案

在当前 `config.py` 中新增 `TCLAW_TRIGGER_PATTERNS` 环境变量，
允许用户自定义触发分析的正则模式：

export TCLAW_TRIGGER_PATTERNS="ERROR|FATAL|EXCEPTION|not found|failed|denied|timeout|refused|traceback|panic|critical"

同时提供三个预设模式（见问题 4 §三）：

| 预设 | 触发模式 | 适用场景 |
|------|---------|---------|
| errors_only (默认) | ERROR\FATAL\|CRITICAL\|PANIC\|SEVERE\|Traceback\|Exception | 生产环境监控 |
| warnings_too | 以上 + WARN\|Warning\|failed\|timeout\|denied\|refused\|not found | 开发调试 |
| everything | .* (每行都触发) | 全量分析，配合 LLM AI 过滤 |

右侧面板 banner 中打印当前使用的触发模式。

四、问题 4：部署时 2 种监听选项 — 全部解释 vs 错误过滤

4.1 方案

在 `tclaw setup` 命令中新增 `--listen` 选项：

| 选项 | 行为 | 右侧工作方式 |
|------|------|------------|
| `--listen errors` (默认) | 只过滤错误行 → 分析 | Live Monitor 检测到匹配行才调 LLM |
| `--listen all` | 每行都分析 | 每行写入 live.log 后立即调 LLM（COOLDOWN 内合并多行一次分析） |

`--listen all` 时 `ERROR_PATTERN` 匹配所有行：

  ERROR_PATTERN = re.compile(r".")   # 匹配一切

`--listen errors` 时使用默认或用户自定义的 `TCLAW_TRIGGER_PATTERNS`。

两种模式写入同一个环境变量 `TCLAW_LISTEN_MODE` (errors|all) 供 live_monitor.py 读取。

五、问题 5：右侧屏幕无法输入指令

5.1 现象

`tclaw live` 启动后进入 `while True` 循环——Python 进程阻塞式的无限循环。
光标移动到右侧面板后按任何键都无反应（被 Tmux 捕获但不传递给 Python）。

5.2 原因

这是**架构层面的取舍**。Live Monitor 本质是一个守护进程——它不需要交互，
只需要持续输出。如果右侧面板需要交互，Live Monitor 必须停止，
右侧重新变回普通 Bash，然后用户手动执行 `tclaw live` 或者 `openclaw agent`。

5.3 方案

方案 A (推荐): 快捷键暂停/恢复

Live Monitor 保持运行，但提供便捷的 Ctrl+Z / Ctrl+L 暂停/恢复机制：

- `Ctrl+L` (L = Live toggle)：暂停 Live Monitor → 右侧变回 Bash → 用户可交互
- 用户敲完命令后，执行 `tclaw live` 恢复监控
- Banner 中提示快捷键

这需要 `live_monitor.py` 监听两个信号——SIGTSTP (Ctrl+Z) 暂停、SIGCONT 恢复。
但 Python 信号处理在子进程中有限制。

方案 B (更简单的近似方案): 双模切换提示

`live_monitor.py` 的 banner 提示用户：

  按 Ctrl+C 停止监控，回到 Bash 执行交互式命令
  重新启动监控: tclaw live

当前用户已经可以做到这一点（Ctrl+C → 自由输入 → 再跑 tclaw live），
只是需要在 banner 中更明确地提示。

方案 C (复杂方案): Python 多线程 + 非阻塞 stdin 监听

Live Monitor 的 `while True` 循环中用 `select.select()` 或 `threading` 同时监听
stdin 和文件变化，允许用户在监控运行中直接输入命令（如 `/analyze 最近 50 行`）。
复杂但有更多可能性——可以支持手动触发分析、切换模式、调整参数等。

5.4 结论

| 方案 | 复杂度 | 用户体验 | 推荐 |
|------|--------|---------|------|
| B: 更明确提示 | 极低 | ⭐⭐⭐ Ctrl+C → 自由输入 → tclaw live | ✅ 近期 (v0.1) |
| C: 多线程 | 高 | ⭐⭐⭐⭐⭐ 边监控边输入命令 | v0.2 |

近期采用方案 B——只需改 banner 文本。v0.2 可考虑方案 C 做完整的交互式右面板。

六、改进优先级与路线图

优先级	问题	难度	建议版本
P0	问题 1: script 代替 tee，全自动日志捕获	中	v0.1
P0	问题 2: TCLAW_INTERPRETER 双模式	低	v0.1
P0	问题 3+4: TCLAW_TRIGGER_PATTERNS + TCLAW_LISTEN_MODE	低	v0.1
P1	问题 5: Banner 交互提示 (方案 B)	极低	v0.1
P2	问题 5: 多线程交互式右面板 (方案 C)	高	v0.2

七、需改动文件清单

文件	改动
terminalclaw/config.py	新增 TCLAW_INTERPRETER, TCLAW_LISTEN_MODE, TCLAW_TRIGGER_PATTERNS
terminalclaw/live_monitor.py	双解释器选择 + 可配置触发模式 + Banner 更新
terminalclaw/tmux_manager.py	init_log_pane() 改为 script 命令
terminalclaw/cli.py	setup 命令新增 --listen 选项
终端侧（WSL2 宿主机）	确保 script 命令可用（Ubuntu 默认自带）

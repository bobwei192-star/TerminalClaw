TerminalClaw 问题文档
记录开发过程中遇到的问题与解决方案

一、Gonzo 借鉴分析结论

问题: 定型设计中 §9.4 提到 Gonzo 是最值得借鉴的日志分析 TUI，但具体可借鉴的内容有哪些？
分析: 克隆 git clone control-theory/gonzo，研究 internal/ai/ 目录。
结论:
  1. Gonzo 的 Ollama 集成模式: 将 OPENAI_API_KEY=ollama + OPENAI_API_BASE=http://localhost:11434
     作为 OpenAI 兼容客户端传入。TerminalClaw 在 config.py 中直接封装了 OLLAMA_API_TAGS 端点，
     比 Gonzo 的 "模拟 OpenAI" 方案更直接。
  2. Gonzo 的 AI Provider Factory 模式 (internal/ai/factory.go): 支持 OpenAI / Claude Code / Auto 三种
     Provider。TerminalClaw 当前只支持 Ollama，但 env_check.py 的架构可以方便地扩展多 Provider。
  3. Gonzo 是 Go 语言 TUI 单体应用，TerminalClaw 是多进程组合（Tmux + Bash + Python）。
     架构哲学不同，不适宜直接移植，但 Provider 设计模式值得参考。

二、Claw Core 借鉴分析结论

问题: Claw Core 的 plugin 架构是否可以复制？
分析: npm install @wchklaus97hk/claw-core，查看 SKILL.md 和 plugin 结构。
结论:
  1. Claw Core 的 openclaw plugins install 模式依赖 OpenClaw 自身 API registerTool()，
     TerminalClaw 作为独立 CLI 不需要立即集成。
  2. 借鉴 Claw Core 的 daemon 管理命令结构 (start/stop/status)，TerminalClaw 的 
     scripts/tclaw.py 已实现对应命令体系。
  3. Claw Core 声明"尚未完全集成"、"可能遇到边缘情况"，印证了设计文档 §11.2 
     的结论：近期保持独立 CLI 形态是最稳妥路径。

三、rejoin .jsonl 会话格式分析

问题: OpenClaw 的 .jsonl 会话文件格式是什么？
分析: 研究 rejoin 源码中读取 ~/.openclaw/agents/**/*.jsonl 的逻辑。
结论:
  1. .jsonl 每行一个 JSON 对象，包含 role, content, timestamp, tokens 等字段。
  2. TerminalClaw 的 session_store.py 实现了兼容的 .jsonl 读写，format_entry() 
     生成的格式与 OpenClaw 原生格式字段兼容。
  3. 未来可以让 TerminalClaw 的分析记录被 rejoin 索引，形成工具链联动。

四、测试用例编写中的问题

问题 4.1: launch_workspace 测试失败 — subprocess.run mock 调用次数不匹配
原因: launch_workspace 内部调用 create_session() 和 split_pane()，这两个函数
      各自又调用了 session_exists() 和 display-message，导致总计 9 次 subprocess.run。
解决: 精确统计调用链，提供 9 个 mock side_effect，其中第 1、2 次返回 returncode=1
      （会话不存在），第 4 次返回 returncode=0（会话已创建），其余返回 returncode=0。

问题 4.2: Windows 环境下 tmux 不可用
分析: tmux 是 Unix 工具，Windows 原生不可用。TerminalClaw 的设计明确要求 WSL2。
解决: pytest 使用 unittest.mock.patch("subprocess.run") 绕过真实 tmux 调用，
      单元测试在 Windows 上可正常运行。集成测试需要在 WSL2 中执行。

五、跨平台兼容性问题

问题 5.1: TCLAW_LOG_DIR 默认 /tmp/tclaw 在 Windows 上不存在
分析: /tmp 是 Unix 路径，Windows 使用 %TEMP% 或 C:\Users\...\AppData\Local\Temp。
解决: config.py 保留 Unix 默认值，通过环境变量覆盖。Windows 用户运行前需设置 
      TCLAW_LOG_DIR 到合适路径。已在 README 中说明此限制。

问题 5.2: tee 命令在 Windows PowerShell 中的行为差异
分析: PowerShell 的 tee 是 Tee-Object，与 Unix tee 语法不同。
解决: 核心日志写入逻辑在 Python log_manager.py 中实现（read_tail、read_grep），
      不依赖 tee 命令。tmux_manager.py 的 init_log_pane 和 Bash 脚本中的 tee 
      仅在 WSL2/Linux 环境生效。

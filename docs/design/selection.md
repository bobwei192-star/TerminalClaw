TerminalClaw 选型决策文档
============================

## 一、候选方案对比

### 1.1 核心方案评估

| 维度 | 方案A：Kitty + 文件中转 | 方案B：Tmux + 文件中转 | 方案C：纯 Gateway 后台 |
|------|------------------------|----------------------|----------------------|
| 面板架构 | 左日志 / 右 OpenClaw CLI | 左日志 / 右 OpenClaw CLI | 无面板，全后台运行 |
| 数据传输方式 | 日志 tee 到文件 → exec cat 读取 | 同左 | cron 定时触发 → exec cat |
| 实时性 | 手动触发，即时 | 手动触发，即时 | 5-30分钟轮询延迟 |
| OpenClaw 集成度 | 右面板跑普通 CLI | 右面板跑普通 CLI | Gateway 原生 daemon 模式 |
| 硬件要求 | GPU 加速渲染，需 Kitty | CPU 渲染，极低 | 无 UI 要求，最低 |
| 跨平台 | Linux/macOS | Linux/macOS/WSL2 ✅ | 全平台 ✅ |
| 会话持久化 | ❌ 关闭终端即丢 | ✅ detach/attach | ✅ systemd 守护 |
| 可封装性 | 中等 | 最高（脚本化极强） | 高（直接装成系统服务） |
| 社区生态 | 小而美 | 巨型（最丰富） | OpenClaw 官方 |

### 1.2 最终选择：方案B（Tmux）

**核心决策理由：**

1. **脚本化能力**：Tmux 的 send-keys 可以精确控制每个面板的行为，这是将整个工作流封装为一键启动工具的前提。Kitty 的 kitten @ 类似但文档和社区案例远不如 Tmux 丰富。

2. **会话持久化**：日志分析场景中，用户可能需要让日志持续运行，自己断开离开，回来再接入。Tmux 的 detach/attach 原生支持这一模式，Kitty 需要额外配置。

3. **WSL2 兼容性**：目标用户可能在 Windows 上开发，Tmux 在 WSL2 中运行最稳定，是近年来 WSL2 环境下的标准终端复用器。

## 二、GitHub 参考项目分析

### 2.1 Gonzo —— 最接近的日志分析 TUI ⭐⭐⭐⭐⭐

- **仓库**：github.com/control-theory/gonzo
- **语言**：Go
- **许可**：MIT
- **核心能力**：实时日志处理、AI 分析集成、Ollama 本地模型支持

**借鉴要点：**
- AI 交互模式证明"选中日志 → 一键 AI 分析"是用户刚需
- Ollama 集成方式（OPENAI_API_KEY=ollama + OPENAI_API_BASE=http://localhost:11434）是本地模型接入的成熟模式
- Severity 过滤的交互设计可作为 TerminalClaw 增强面板的参考

### 2.2 TmuxAI —— Tmux 原生 AI 助手 ⭐⭐⭐⭐

**借鉴要点：**
- 证明了"Tmux + AI 面板"架构的可行性
- 上下文收集机制值得参考

### 2.3 Claw Core —— OpenClaw 插件化参考 ⭐⭐⭐⭐

- **npm**：@wchklaus97hk/claw-core
- **许可**：MIT

**借鉴要点：**
- 插件化架构设计
- daemon 管理命令结构（start/stop/status）

### 2.4 rejoin —— AI Agent 会话管理 ⭐⭐⭐⭐⭐

- **PyPI**：rejoin
- **语言**：Python
- **许可**：MIT

**借鉴要点：**
- OpenClaw .jsonl 会话文件读取逻辑
- Tmux 原生集成（回车键直接在新窗口恢复会话）

## 三、差异化定位

| 维度 | Gonzo | TmuxAI | TerminalClaw |
|------|-------|--------|-------------|
| AI 模型 | 可选付费 API | 必须 OpenRouter 付费 | Ollama 本地免费 ✅ |
| 面板架构 | 单体 TUI | Tmux 内嵌面板 | Tmux 原生分屏 ✅ |
| Agent 框架 | 自研 | 自研 | OpenClaw 生态 ✅ |
| 可扩展性 | 固定功能 | 固定功能 | OpenClaw Skills 可插拔 ✅ |

## 四、OpenClaw vs Hermes 对比

### 4.1 架构差异

| 维度 | OpenClaw | Hermes Agent |
|------|---------|-------------|
| 设计定位 | AI Agent 框架 — 可编程的工具编排层 | 个人 AI 助手 — 面向消费者的完整产品 |
| 被调方式 | `openclaw agent -m "prompt"` 可作为子进程调用 | `hermes` 启动后进入 TUI 交互，无可编程 CLI 分析模式 |
| 终端嵌入 | 可在 tmux 面板中作为独立进程运行 | TUI 占满整个终端，设计为"你坐在它面前对话" |
| 程序化调用 | ✅ subprocess + prompt 即可 | ❌ 无等价 CLI -m 模式 |

### 4.2 结论

**不建议替换为 Hermes**：
- TerminalClaw 需要的是"可被子进程调用的 Agent 运行时"
- Hermes 是"面向终端用户的 TUI 对话应用"
- 两者的交互模型完全不同

## 五、社区对标分析

### 5.1 通用终端 AI 方案

| 项目 | AI 模型 | 成本 | 架构 | TerminalClaw 优势 |
|------|---------|------|------|------------------|
| Gonzo | 可选付费 API | 需 API Key | 单体 TUI | 面板分离更灵活 |
| TmuxAI | OpenRouter 付费 | 按量付费 | Tmux 双面板 | 完全免费本地模型 |
| Warp Oz Agent | GPT-4/Claude | $18-180/月 | 终端内嵌闭源 | 开源、免费、可控 |

### 5.2 差异化总结

TerminalClaw 的组合（终端内双面板 + 通用日志分析 + 全本地 Ollama + 一键封装 + 完全免费）在现有生态中是独特的。

| 维度 | TroyKelly | Oh-My-OpenClaw | tmux Skill | Security Log Analyzer | TerminalClaw |
|------|-----------|----------------|------------|----------------------|-------------|
| 终端内双面板 | ❌ Web UI | ❌ 后台运行 | ❌ 无面板 | ❌ 无面板 | ✅ 终端内 |
| 通用日志分析 | ❌ 通用终端 | ❌ 通用 Agent | ❌ 通用终端 | ⚠️ 仅安全日志 | ✅ 通用日志 |
| 全本地 Ollama | ❌ 依赖 API | ❌ 依赖 API | ❌ 依赖 API | ❌ 云端 API | ✅ 零外部依赖 |
| 一键封装 | ❌ 需多步配置 | ❌ 需 npm 安装 | ⚠️ 需手动加载 | ❌ 需 Skill 配置 | ✅ npm 一键 |
| 免费无 API | ❌ 需 API Key | ❌ 需 API Key | ❌ 需 API Key | ❌ 需 API Key | ✅ 完全免费 |
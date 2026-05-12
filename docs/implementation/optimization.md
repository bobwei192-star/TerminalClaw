TerminalClaw 优化方案文档
==========================

## 一、性能优化

### 1.1 OpenClaw 延迟优化

**问题**：OpenClaw Agent 冷启动时间超过 60 秒，无法满足实时性需求。

**解决方案：**

#### ① 启用 Lean Mode

```json
// ~/.openclaw/openclaw.json
{
  "agents": {
    "defaults": {
      "experimental": { "localModelLean": true }
    }
  }
}
```

效果：砍掉 browser、cron、message 等默认重工具，只保留 memory_search、exec、sessions_spawn。

#### ② Context Pruning + TTL

```json
{
  "agents": {
    "defaults": {
      "contextPruning": { "mode": "cache-ttl", "ttl": "5m" }
    }
  }
}
```

效果：旧工具结果自动修剪，不占用上下文。

#### ③ Ollama 常驻内存

```bash
# 设置环境变量
export OLLAMA_KEEP_ALIVE=86400

# 或启动时指定
ollama run terminalclaw --keepalive 24h
```

#### ④ 日志预处理

在 `log_manager.py` 中添加智能摘要逻辑：

```python
async def smart_summarize(log_content):
    if len(log_content) > 500:
        # 1. 本地轻量模型提取 ERROR/FATAL
        error_lines = await light_model.extract_critical(log_content)
        # 2. 附加上下文
        context = extract_surrounding_lines(log_content, error_lines, radius=3)
        # 3. 整合发送
        return f"关键错误:\n{context}\n\n完整日志已归档，需要时可用 'tclaw full-logs' 查看"
    return log_content
```

### 1.2 模型分层路由

| 场景 | 模型选择 | 延迟 |
|------|---------|------|
| 简单解释/摘要 | qwen3:0.6b（本地） | < 3s |
| 复杂根因分析 | qwen3:32b 或 deepseek-v4 | < 15s |
| 代码生成 | codex 或 claude-opus（远程） | 按需 |

## 二、功能优化

### 2.1 全自动日志捕获

**问题**：用户必须手动添加 `| tee -a /tmp/tclaw/live.log`。

**解决方案**：使用 `script` 命令接管整个 Shell Session

修改 `tmux_manager.py` 中的 `init_log_pane()` 函数：

```python
def init_log_pane(session: str, pane: str, log_command: str) -> None:
    log_dir = "/tmp/tclaw"
    log_file = f"{log_dir}/live.log"
    send_keys(session, pane, f"mkdir -p {log_dir}")
    # 使用 script 命令代替 tee
    script_cmd = f"script -q -f -a {log_file} -c 'bash'"
    send_keys(session, pane, script_cmd)
    send_keys(session, pane, f"echo '=== TerminalClaw 日志监控启动 ==='")
    send_keys(session, pane, f"echo '日志文件: {log_file}'")
    send_keys(session, pane, log_command)
```

效果：用户在左面板做的任何事情全部自动写入 live.log。

### 2.2 双引擎路由层

**设计方案**：

```
用户输入命令 → TerminalClaw 判断复杂度 → 
  ├── 简单查询（"这是什么意思"）→ 轻量 LLM API / 本地小模型（2-3s）
  ├── 复杂排障（"为什么报错"）→ OpenClaw 深度分析（10-15s）
  └── 需要记忆/上下文 → 强制走 OpenClaw
```

**实现**：在 `cli.py` 中添加路由逻辑：

```python
def route_query(input_text: str) -> str:
    """根据查询复杂度选择解释器"""
    complexity = assess_complexity(input_text)
    
    if complexity == "simple":
        return "direct_api"  # 轻量查询走 API 直连
    elif needs_context(input_text):
        return "openclaw_agent"  # 需要记忆走 OpenClaw
    else:
        # 根据配置选择
        return os.getenv("TCLAW_INTERPRETER", "direct_api")
```

**状态条显示**：在 Tmux 右屏顶部加 ANSI 状态条：
- `[MODE: FAST]` 绿色 - API 直连模式
- `[MODE: DEEP]` 黄色 - OpenClaw Agent 模式
- 用户按 `Ctrl+T` 切换

### 2.3 可配置触发模式

**问题**：当前只检测 ERROR/FATAL 等固定关键字，用户需要自定义。

**解决方案**：添加 `TCLAW_TRIGGER_PATTERNS` 环境变量

```bash
# 自定义触发模式
export TCLAW_TRIGGER_PATTERNS="ERROR|FATAL|EXCEPTION|not found|failed|denied|timeout|refused"
```

**预设模式**：

| 预设 | 触发模式 | 适用场景 |
|------|---------|---------|
| errors_only | ERROR\|FATAL\|CRITICAL\|PANIC\|SEVERE\|Traceback\|Exception | 生产环境监控 |
| warnings_too | 以上 + WARN\|Warning\|failed\|timeout\|denied\|refused\|not found | 开发调试 |
| everything | .* (每行都触发) | 全量分析 |

**实现**：在 `live_monitor.py` 中读取并解析：

```python
def get_trigger_patterns() -> re.Pattern:
    """获取触发分析的正则模式"""
    patterns = os.getenv("TCLAW_TRIGGER_PATTERNS", 
                        "ERROR|FATAL|EXCEPTION|CRITICAL|PANIC|SEVERE|Traceback")
    return re.compile(patterns, re.IGNORECASE)
```

### 2.4 监听模式切换

**问题**：用户需要两种监听模式：只分析错误 vs 分析所有内容。

**解决方案**：添加 `TCLAW_LISTEN_MODE` 环境变量

```bash
# 只监听错误（默认）
export TCLAW_LISTEN_MODE="errors"

# 监听所有输出
export TCLAW_LISTEN_MODE="all"
```

**CLI 命令**：

```bash
# 设置监听模式
tclaw setup --listen errors
tclaw setup --listen all
```

### 2.5 右面板交互性

**问题**：右侧面板运行 Live Monitor 循环，无法输入指令。

**方案 B（近期）**：改进提示信息

在 `live_monitor.py` 的 banner 中添加提示：

```python
def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              TerminalClaw Live Monitor                       ║
║              实时日志分析 · 自动错误检测                      ║
╠══════════════════════════════════════════════════════════════╣
║  日志文件: /tmp/tclaw/live.log                              ║
║  扫描间隔: 3.0 秒                                           ║
║                                                             ║
║  操作提示:                                                   ║
║    Ctrl+C    → 停止监控，回到 Bash 执行交互式命令            ║
║    tclaw live → 重新启动监控                                 ║
║                                                             ║
║  当前模式: {mode} | 触发模式: {trigger}                      ║
╚══════════════════════════════════════════════════════════════╝
    """.format(mode=get_mode_label(), trigger=get_trigger_label()))
```

**方案 C（v0.2）**：多线程交互式面板

```python
def start_interactive_monitor():
    """启动交互式监控（支持边监控边输入）"""
    # 启动日志监控线程
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    # 监听用户输入
    while True:
        try:
            user_input = input("\n> ")
            handle_user_command(user_input)
        except EOFError:
            break
```

## 三、记忆系统优化

### 3.1 自动知识提取

**方案**：安装 OpenClaw auto-capture hook，每次会话结束后自动把关键决策写入 MEMORY.md

```bash
# 安装 auto-capture hook
openclaw hooks install auto-capture
```

### 3.2 会话历史同步

在 `session_store.py` 中添加同步逻辑：

```python
def sync_to_openclaw_memory():
    """每天凌晨把命令历史转成 OpenClaw 记忆格式"""
    entries = read_entries(LOG_PATH)
    summary = local_lightweight_model.summarize(entries)  # 轻量模型先压缩
    append_to_memory_md(summary, category="terminal_history")
```

### 3.3 触发 Dreaming 机制

添加 `tclaw evolve` 命令：

```bash
tclaw evolve   # 触发 OpenClaw 的 dreaming + compaction
```

**效果**：
- 把短期会话记忆压缩成长期知识
- 发现用户命令模式
- 生成针对性建议，写回 USER.md

## 四、指令库索引化

### 4.1 Skill 化的指令图谱

按领域拆 Skill：

| Skill | 指令数量 | 领域 |
|-------|---------|------|
| k8s-debug-skill | 500 | Pod/Node/Service 排障 |
| db-debug-skill | 500 | SQL/Redis/Mongo 排障 |
| net-debug-skill | 500 | tcpdump/curl/netstat 组合 |
| linux-debug-skill | 1500 | 通用性能/内存/IO 分析 |

### 4.2 语义检索暴露

**实现逻辑**：

```python
def suggest_commands(error_text: str) -> List[str]:
    """根据错误文本推荐排障指令"""
    # 1. 提取错误关键词
    keywords = extract_keywords(error_text)
    
    # 2. 在指令库中语义检索
    results = semantic_search(keywords, top_k=3)
    
    # 3. 返回建议
    return [result["command"] for result in results]
```

**展示方式**：

```
[检测到 OOMKilled]
建议排查链路：
1. kubectl describe pod <pod> | grep -A 5 "Last State"
2. dmesg | grep -i "killed process"
3. cat /sys/fs/cgroup/memory/memory.limit_in_bytes

[按 Enter 执行第1条 / 按 2 执行第2条 / 按 c 复制]
```

## 五、优化优先级路线图

| 优先级 | 优化项 | 难度 | 预期效果 | 建议版本 |
|--------|--------|------|----------|----------|
| P0 | script 代替 tee，全自动日志捕获 | 中 | 用户无需手动加管道 | v0.1 |
| P0 | TCLAW_INTERPRETER 双模式 | 低 | 支持 API 直连/OpenClaw 切换 | v0.1 |
| P0 | TCLAW_TRIGGER_PATTERNS + TCLAW_LISTEN_MODE | 低 | 可配置触发条件 | v0.1 |
| P1 | Banner 交互提示 | 极低 | 提升用户体验 | v0.1 |
| P1 | OpenClaw Lean Mode 优化 | 低 | 延迟从 60s 降至 15s | v0.1 |
| P2 | 多线程交互式右面板 | 高 | 边监控边输入命令 | v0.2 |
| P2 | 指令库索引化 | 中 | 情境化排障建议 | v0.2 |
| P3 | 记忆系统整合 | 中 | 命令历史进化 | v0.3 |
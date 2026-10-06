# 改写映射（Claude Code / Codex → WorkBuddy）

`scripts/port_skill.py` 内置的 `TOOL_MAP` 就是这张表。需要新增规则时同时改脚本与本文档。

## 一、专有工具名 / 编排写法

| # | 上游（正则） | 改写为 | 原由 |
|---|---|---|---|
| 1 | `Task\s*工具` | `Agent 工具` | WorkBuddy 的并行子代理工具名是 `Agent` |
| 2 | `Team\s*工具` | `Agent 工具` | 同上，WorkBuddy 无独立 Team 工具 |
| 3 | `使用 TeamCreate 创建团队：` | `WorkBuddy 无需预先创建团队对象，你本人即 team-lead：` | WorkBuddy 没有团队对象，靠并发 Agent 调用实现 |
| 4 | `- \`team_name\`:` / `- team_name:` | `- \`name\`:` | Agent 工具的团队标识参数叫 `name` |
| 5 | `- \`agent_type\`: \`team-lead\`` | `- 子代理类型：\`general-purpose\`` | WorkBuddy 用 `subagent_type`，取值不同 |
| 6 | `向4个Agent发送 shutdown_request（使用 SendMessage，type: "shutdown_request"）` | `全部报告收到即可直接汇总。WorkBuddy 的子代理在返回结果后自然结束，无需显式的关闭握手。` | 无关闭握手协议 |
| 7 | `通过 SendMessage 把完整分析报告发送给 team-lead（type: "message", recipient: "team-lead"）` | `把完整分析报告作为最终返回值输出（WorkBuddy 中子代理的返回值会自动回到主代理）` | 子代理返回值自动回流，无需显式发消息 |

## 二、路径前缀重写

`PATH_MAP = ["tools/", "skills/", "reports/", "assets/"]`

正则 `(?<![\w\-/{])<prefix>` —— 负向后顾避免误伤 `src/tools/`、`my-tools/`、`/tools/` 这类已带前缀的写法。
替换为 `{SKILL_ROOT}/<prefix>`。

**另需人工处理**（脚本只做 scan 高亮，不自动改）：

| 写法 | 处理 |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | 改指 `{SKILL_ROOT}/SOURCE.md` 或入口 `SKILL.md` |
| `.claude/settings.local.json` | 改写为「联网能力预检」小节，保留原意（防止无网络时静默退化为伪研究） |
| `.codex/` | 确认是否适用，不适用则删除 |

## 三、无需改写（WorkBuddy 同名存在）

- `subagent_type`
- `run_in_background`
- `TaskCreate` / `TaskList` / `TaskUpdate` / `TaskGet`
- `SendMessage`
- `$ARGUMENTS`（保留原样，在顶部注释块说明含义）

## 四、frontmatter 规格

每个子技能文件顶部必须为：

```yaml
---
name: <slug>
description: <一句话说明，用于路由匹配>
agent_created: true
---
```

- `name`：小写连字符，与文件名去扩展名一致
- `description`：**路由命中的唯一依据**，写「做什么 + 什么场景触发」，别复述文件名
- `agent_created: true`：标记为模型创建的技能，允许后续用 SkillManage 维护

`convert` 会先剥离上游已有的旧 frontmatter 再写入新 frontmatter（避免重复块）。

## 五、适配说明注释块

脚本自动插在每个子技能正文之前：

```html
<!-- WorkBuddy 适配说明
  $ARGUMENTS   = 用户本轮指定的标的 / 主题，执行时替换为实际值
  {SKILL_ROOT} = <技能根绝对路径>
  Python       = <python 解释器绝对路径>
  文中「Agent 工具」= WorkBuddy 的并行子代理，在同一条消息内并发调用多次即可真正并行
-->
```

新版 Python 解释器路径应写成绝对路径 —— 跨机复制后 `sys.executable` 会变，
必要时让子技能在运行时重新定位（`python -c "import sys;print(sys.executable)"`）。

## 六、需要人工判断的高危写法（scan 会高亮）

| 关键词 | 含义 | 处理 |
|---|---|---|
| `\.claude/settings` | Claude 权限白名单 | 改「联网能力预检」 |
| `dangerously-skip-permissions` | 关闭全部工具审批 | **删除该建议** |
| `TeamCreate\|shutdown_request` | 团队编排 | 脚本可自动处理，但需人工复核 |
| `\$ARGUMENTS` | 斜杠命令参数 | 顶部注释块解释 |
| `CLAUDE\.md` / `AGENTS\.md` | 项目规范文件 | 改指新位置 |

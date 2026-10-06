# 移植验收清单与故障对照

## 一、验收清单（逐条勾，缺一不可）

### 结构层
- [ ] `~/.workbuddy/skills/<name>/SKILL.md` 存在，且是**一级文件**
- [ ] `SKILL.md` frontmatter 含 `name` / `description` / `agent_created: true`
- [ ] `description` 写的是「做什么 + 什么触发」，**不含 `TODO`**
- [ ] `LICENSE` 已从上游原样保留
- [ ] 写了 `SOURCE.md`（上游地址、commit/日期、已做改写清单）
- [ ] 子技能数 ≥ 上游可执行单元数（无遗漏）

### 内容层
- [ ] 路由表里出现的每个引用路径**全部命中**（用脚本逐条 exists 校验）
- [ ] 全部子技能 frontmatter **零不合规**
- [ ] 专有写法残留**清零**（见下方复扫命令）
- [ ] `dangerously-skip-permissions` 等危险建议已删除
- [ ] `$ARGUMENTS` 保留但已在顶部注释块解释

### 运行层
- [ ] `tools/` 下脚本用 `python -c "import ast;ast.parse(open(f).read())"` 逐个语法检查通过
- [ ] **实跑至少一个真实业务工具**，看到完整算式 / 输出（不是只 import 成功）
- [ ] 统计外部依赖：明确哪些是纯标准库、哪些需额外装包

### 分发层
- [ ] zip 保留顶层目录前缀
- [ ] zip 完整性校验通过（`testzip()` 返回 None）
- [ ] **解压到临时目录后 `SKILL.md` 层级正确**
- [ ] **解压目录内的脚本可直接运行**（证明无硬编码绝对路径依赖）

## 二、复扫命令

### 查专有写法残留

```bash
cd ~/.workbuddy/skills/<name>

# ⚠️ 含反引号的模式必须用单引号，否则 bash 会做命令替换，把正则变残缺并刷出整个文件
grep -rn -E 'Task 工具|Team 工具|TeamCreate|shutdown_request|team_name|\.claude/|dangerously-skip-permissions' . || echo "干净"

# 复查 agent_type 时要精确匹配，别误伤合法的 subagent_type
grep -rn -E '(^|[^b])agent_type' . || echo "干净"
grep -rn 'subagent_type' .        # 这是合法参数，命中正常，不用改
```

> 坑：`grep -rn 'agent_type'` 会**同时命中 `subagent_type`**。必须用负向断言或先排除。
> 坑：在 bash 里写 `grep "…\`xxx\`…"` 会触发**反引号命令替换**，必须用单引号包裹模式。

### 校验路由表引用全部命中

```bash
python - <<'PY'
import re, os, pathlib
root = pathlib.Path(os.path.expanduser("~/.workbuddy/skills/<name>"))
txt = (root/"SKILL.md").read_text(encoding="utf-8")
refs = sorted(set(re.findall(r"references/skills/[\w\-.]+\.md", txt)))
miss = [r for r in refs if not (root/r).exists()]
print("引用 %d 条，缺失 %d 条" % (len(refs), len(miss)))
for m in miss: print("  MISS", m)
PY
```

### 校验 frontmatter 合规

```bash
python - <<'PY'
import os, pathlib
root = pathlib.Path(os.path.expanduser("~/.workbuddy/skills/<name>/references/skills"))
bad = []
for p in sorted(root.glob("*.md")):
    head = p.read_text(encoding="utf-8")[:200]
    if not head.startswith("---") or "name:" not in head or "description:" not in head:
        bad.append(p.name)
print("不合规 %d / %d" % (len(bad), len(list(root.glob('*.md')))))
for b in bad: print("  BAD", b)
PY
```

## 三、故障对照表

| 症状 | 根因 | 处理 |
|---|---|---|
| 技能列表里完全不出现 | `SKILL.md` 不在技能根目录一级 / 缺 frontmatter | 检查层级；补 `name`+`description`+`agent_created` |
| 出现了但从不被触发 | `description` 太笼统或写成 `TODO` | 重写 description，加入用户口语触发词 |
| 装了 0 个技能（明明有几十个文件） | 上游是平铺的 `*.md` 命令，未被重构成单入口 | 走「单入口 + 渐进式披露」，只注册一个入口 |
| 子技能读不到工具 | 路径仍写 `tools/x.py` 相对路径 | 改为 `{SKILL_ROOT}/tools/x.py` |
| 解压后技能装不上 | zip 没保留顶层目录前缀，`SKILL.md` 落在解压根目录 | 重新打包，写入路径带 `<name>/` 前缀 |
| 类加载/编码报错 | Windows 下非 ASCII 路径写进 `.ps1`/`.bat` | 用直接命令调用，不要写脚本文件 |
| `EOFError: ... end-of-stream marker` | tar.gz 下载被 `--max-time` 截断 | 不是包损坏。加大超时到 300s+，或用 trees API |
| `HTTP 000`（`raw.githubusercontent.com`） | 该域名在大陆被定向阻断 | 改用 `api.github.com/.../contents/` + `Accept: application/vnd.github.raw` |
| 脚本语法检查通过但一跑就崩 | 未实跑验证 | **语法检查 ≠ 能运行**。必须真跑一个工具 |
| `scan` 报告「候选技能文件：0 个」 | 源目录路径写错（`os.walk` 对不存在的目录静默返回空） | 脚本已加兜底：源目录不存在会直接 `[FAIL]` 退出码 2。若仍为 0，确认 src 是否指到了子目录 |
| 子技能顶部注释块里的绝对路径不对 | `--root` 写成了别的路径（如测试用的占位值） | 脚本已加 `[WARN]`。重跑并让 `--root` = 目标目录绝对路径 |
| 部分技能 description 仍是 `TODO` | `desc.json` 的键与 `.md` 文件名对不上 | 脚本会列出「没有对应技能的键」。键必须等于文件名去扩展名 |

## 四、实跑验证的记录模板

移植完成后，至少在 `SOURCE.md` 记一行：

```
实跑验证（<日期>）：
- tools/<x>.py <子命令>  → 输出正常（<关键数字/算式>）
- tools/<y>.py <子命令>  → 输出正常
- 依赖统计：N 个工具纯标准库，M 个需 <包名>
```

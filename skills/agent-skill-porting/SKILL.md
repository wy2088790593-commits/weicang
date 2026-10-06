---
name: agent-skill-porting
description: 把第三方 agent skill 仓库（Claude Code 的 ~/.claude/skills/、Codex 的 ~/.codex/skills/、或任意 SKILL.md 集合）机械转换成 WorkBuddy 可加载的技能。覆盖：frontmatter 补写、专有工具名改写、路径重写、单入口+渐进式披露架构、打包分发与验收。适用于「把这个 skill 装上」「移植/转换/适配这个技能包」「Claude Code skill 在 WorkBuddy 怎么用」「这个 skill 装不上」。触发词：移植技能、转换 skill、装第三方技能、skill 不兼容、Claude Code skill、Codex skill、port skill、技能适配。
agent_created: true
---

# 第三方 Agent Skill → WorkBuddy 移植

把别人写好的 skill 仓库，改造成 WorkBuddy 的 `~/.workbuddy/skills/<name>/` 能直接加载的技能。

## 何时使用

- 用户给了一个 GitHub 仓库 / zip，说「装上」「移植过来」「转成 WorkBuddy 能用的」
- 用户拿到 Claude Code 的 `.claude/skills/*.md` 或 Codex 的 `.codex/skills/*/SKILL.md`，装到 WorkBuddy 后**不生效**
- 技能列表里出现 `TODO:` 占位描述、或技能完全不出现
- 需要把一批技能打包成**可跨电脑复制**的压缩包

## 核心认知：两套格式的差异

| 维度 | Claude Code | Codex | **WorkBuddy** |
|---|---|---|---|
| 技能根目录 | `~/.claude/skills/` | `~/.codex/skills/` | **`~/.workbuddy/skills/`** |
| 入口文件 | `skills/<name>.md`（**常无 frontmatter**） | `<name>/SKILL.md` | **`<name>/SKILL.md`** |
| 必备 frontmatter | 无 | 部分有 | **`name` / `description` / `agent_created`** |
| 调用方式 | 斜杠命令 `/name`，参数 `$ARGUMENTS` | 自动加载 | 按 `description` 语义匹配自动加载，**无斜杠参数替换** |
| 注册粒度 | 每个 `.md` 一个命令 | 每个目录一个技能 | **每个目录一个技能**（目录内多层文件不会被单独注册） |

**最关键的一条差异**：WorkBuddy 只识别「技能根目录下的一级 `SKILL.md`」。
上游那种「21 个斜杠命令 = 21 个 `.md` 平铺文件」的结构，**直接拷过去等于装了 0 个技能**。
必须重构成「单入口 + 渐进式披露」（见下方架构决策）。

## 架构决策：单入口 + 渐进式披露

上游若有很多子技能（经验阈值：**超过 5 个**），**不要**把每个都注册成独立技能 —— 会塞爆技能列表、
污染路由匹配。正确做法：

```
~/.workbuddy/skills/<name>/
├── SKILL.md                  # 唯一入口：索引表 + 调用协议 + 铁律
├── README.md                 # 跨机安装说明
├── SOURCE.md                 # 上游出处、版本、许可、已做的改写（便于日后更新）
├── LICENSE                   # 原样保留上游协议（MIT/Apache 等必留）
├── references/skills/*.md    # N 个子技能，带 frontmatter，**按需读取**，不注册
├── tools/*.py                # 上游工具原样搬入，SKILL.md 里指到 {SKILL_ROOT}/tools/
├── assets/                   # 配图、模板
└── reports/                  # 输出目录（约定，可空）
```

入口 `SKILL.md` 里必须有一张**路由表**：`用户说什么 → 读哪个 references/skills/*.md`。
主代理先读入口、再按需 `Read` 子技能文件，这就是「渐进式披露」。

## 工作流

### 第 1 步：拿到源码并核对真实结构

**不要只看 README**。优先整包下载后本地核对：

```bash
# codeload 通常可直连，不受 github.com 主站定向阻断影响
curl -L --noproxy '*' --max-time 300 \
  -o repo.tar.gz \
  "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main"
```

> ⚠️ **大仓会被超时截断**：`--max-time 60` 下约 571 KB/s，60 秒只能下 34 MB。
> 解压时会报 `EOFError: Compressed file ended before the end-of-stream marker was reached` ——
> 这是**下载被截断，不是包损坏**。大仓给到 300s 以上，且解压前先用 `tarfile` 验证完整性。
> 备选：`api.github.com/repos/{o}/{r}/git/trees/{branch}?recursive=1` 一次拿完整文件树（1 次 core 额度）。
> 注意 `raw.githubusercontent.com` 在大陆**常被定向阻断**，读单文件改用
> `api.github.com/repos/{o}/{r}/contents/{path}` + `-H "Accept: application/vnd.github.raw"`。

### 第 2 步：scan 诊断

```bash
python scripts/port_skill.py scan <src_dir>
```

输出：候选文件数、有无 frontmatter、需要人工判断的写法（`.claude/settings`、`CLAUDE.md`、
`dangerously-skip-permissions`、`$ARGUMENTS` 等）、内部路径引用统计、子目录规模。

### 第 3 步：编写 slug → description 映射

`convert` 需要一份 JSON：`{"<文件名去扩展名>": "<一句话说明>"}`。

**description 是路由命中的唯一依据**，必须写清「这个技能做什么 + 什么场景触发它」，
不能写成「TODO」或复述文件名。写成用户会说的话（含中文口语触发词）效果最好。

### 第 4 步：convert 机械转换

```bash
python scripts/port_skill.py convert <src_dir> <dst_dir> \
  --root "<dst_dir 绝对路径>" \
  --python "<python 解释器绝对路径>" \
  --desc-file desc.json
```

脚本自动完成：加 frontmatter、剥离旧 frontmatter、路径前缀 → `{SKILL_ROOT}/`、
专有工具名替换、插入顶部适配说明注释块、复制 `tools/` 与 `LICENSE`。

### 第 5 步（**必做，脚本不做**）：收尾四件事

1. **手写入口 `SKILL.md`**（路由表 + 调用协议 + 铁律）
2. **补回所有缺 description 的技能**（脚本会列出 `!! ... 缺少 description 映射`）
3. **全目录复扫专有写法残留** —— 不能只验抽样的那个文件
4. **实跑至少一个工具**，确认端到端可用（见 references/checklist.md）

> 第 3 条是踩过的坑：当时只改了 `investment-team.md` 的团队编排，
> **漏了 `news-pulse.md` / `private-research.md`** 也含同类写法。批次改写后必须全目录复扫。

## 改写映射表（可复用）

| 上游写法 | 改写为 |
|---|---|
| `$ARGUMENTS` | **保留**，在文件顶部注释块说明含义（WorkBuddy 无斜杠参数替换） |
| `Task 工具` / `Team 工具` | `Agent 工具` |
| `TeamCreate` 创建团队 | 「你本人即 team-lead，并发调用 Agent 时用 `name` 指定角色」 |
| `team_name` 参数 | `name` 参数 |
| 子代理 `shutdown_request` | 「子代理返回结果后自然结束，无需关闭握手」 |
| 子代理用 `SendMessage` 汇报 | 「把报告作为最终返回值输出」 |
| `.claude/settings.local.json` 权限预检 | 「联网能力预检」（保留原意：防止无网络时静默退化为伪研究） |
| `tools/` `skills/` `reports/` `assets/` `CLAUDE.md` | 统一改指 `{SKILL_ROOT}/...` |
| `claude --dangerously-skip-permissions` | **删除该建议**，改为正常授权提示 |

**不用改的**：`subagent_type` / `run_in_background` / `TaskCreate` / `SendMessage` ——
这些在 WorkBuddy 中同名存在且语义一致。

完整映射（含正则）见 `references/mapping.md`。

## 打包分发（跨机可用）

用自带脚本一把梭（打包 + 完整性校验 + 解压演练）：

```bash
python scripts/pack_skill.py ~/.workbuddy/skills/<name> -o <name>-skill.zip
```

脚本会做三件事：保留顶层目录前缀打包、`testzip()` 校验完整性、
解压到临时目录确认 `SKILL.md` 层级正确，且 `scripts/` 与 `tools/` 下的 `.py` 全部可编译。

<details>
<summary>不想用脚本时的手工等价做法</summary>

```bash
python -c "
import zipfile, os
root = os.path.expanduser('~/.workbuddy/skills/<name>')
with zipfile.ZipFile('<name>-skill.zip','w',zipfile.ZIP_DEFLATED) as z:
    for dp,_,fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp,f)
            z.write(p, os.path.join('<name>', os.path.relpath(p, root)))
"
```

</details>

> ⚠️ **必须保留顶层文件夹前缀**，否则解压后 `SKILL.md` 层级不对，技能无法被识别。
> 本机通常**没有 `zip` 命令**，用 Python `zipfile`。

对方电脑安装：解压到 `~/.workbuddy/skills/`（Windows 为 `C:\Users\<用户>\.workbuddy\skills\`），
重启会话即生效。

## 铁律

1. **不注册超过 5 个/仓库的新技能** —— 走单入口 + 渐进式披露
2. **`LICENSE` 必须原样保留** —— 上游是 MIT/Apache 就照搬，别丢
3. **`SOURCE.md` 必写** —— 记上游地址、commit/日期、已做的全部改写，否则日后无法同步上游更新
4. **危险开关一律不继承** —— `--dangerously-skip-permissions`、关闭审批等建议必须删掉
5. **实跑验证 > 静态检查** —— 语法正确不代表能跑，必须真跑一个工具
6. **改完必须全目录复扫** —— 漏一个文件就等于没改

## 相关资源

- `references/mapping.md` —— 完整改写映射（含正则与原由）
- `references/checklist.md` —— 移植后验收清单、常见故障对照表
- `scripts/port_skill.py` —— `scan` / `convert` 双模式（纯标准库）
- `scripts/pack_skill.py` —— 打包 + 校验 + 解压演练（纯标准库）

## 脚本速查

```bash
S=scripts   # 相对技能目录

# 诊断：有哪些文件、哪些要手工改
python $S/port_skill.py scan  <src>

# 转换：加 frontmatter + 改写工具名 + 重写路径 + 复制 tools/LICENSE
python $S/port_skill.py convert <src> <dst> \
    --root <dst 绝对路径> --python <python 绝对路径> --desc-file desc.json

# 打包：保留顶层前缀 + 全景校验
python $S/pack_skill.py <skill_dir> -o <name>-skill.zip
```

**行为约定**：源目录不存在 → 直接 `[FAIL]` 退出（退出码 2）；`--root` 与目标目录不一致 → `[WARN]`；
`desc.json` 里有对不上技能文件的键 → `[WARN]`（多半是拼写错误）。

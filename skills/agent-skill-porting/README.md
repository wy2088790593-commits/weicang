# agent-skill-porting

把第三方 agent skill 仓库（Claude Code 的 `~/.claude/skills/`、Codex 的 `~/.codex/skills/`、
或任意 `SKILL.md` 集合）机械转换成 WorkBuddy 可加载的技能。

## 解决什么问题

别人的技能包直接拷进 `~/.workbuddy/skills/` 为什么装不上？

| 维度 | Claude Code | Codex | **WorkBuddy** |
|---|---|---|---|
| 技能根目录 | `~/.claude/skills/` | `~/.codex/skills/` | **`~/.workbuddy/skills/`** |
| 入口文件 | `skills/<name>.md`（常无 frontmatter） | `<name>/SKILL.md` | **`<name>/SKILL.md`** |
| 必备 frontmatter | 无 | 部分有 | **`name` / `description` / `agent_created`** |
| 调用方式 | 斜杠命令 `/name`，参数 `$ARGUMENTS` | 自动加载 | 按 `description` 语义匹配自动加载，**无斜杠参数替换** |
| 注册粒度 | 每个 `.md` 一个命令 | 每个目录一个技能 | **每个目录一个技能**（多层文件不单独注册） |

最关键的一条：WorkBuddy 只识别**技能根目录下的一级 `SKILL.md`**。
上游那种「21 个斜杠命令 = 21 个平铺 `.md`」的结构，**直接拷过去等于装了 0 个技能** ——
必须重构成「单入口 + 渐进式披露」。

## 文件清单

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 技能入口：格式差异对照、单入口架构、五步工作流、改写映射速查、六条铁律、脚本速查 |
| `references/mapping.md` | 完整改写映射（含正则与原由）、路径重写规则、frontmatter 规格、高危写法处理 |
| `references/checklist.md` | 四层验收清单、三段可复制的复扫脚本、9 类故障对照表、实跑记录模板 |
| `scripts/port_skill.py` | `scan` / `convert` 双模式，纯 Python 标准库 |
| `scripts/pack_skill.py` | 打包 + 完整性校验 + 解压演练，纯 Python 标准库 |

## 快速试用

```bash
cd <本技能目录>

# 1) 拿一个上游仓库先做诊断
python scripts/port_skill.py scan  /path/to/upstream-repo

# 2) 写一份 slug -> description 映射（description 是路由命中的唯一依据）
cat > desc.json <<'EOF'
{"my-skill-a": "一句话说明 A 做什么、什么场景触发。",
 "my-skill-b": "一句话说明 B 做什么、什么场景触发。"}
EOF

# 3) 执行转换
python scripts/port_skill.py convert /path/to/upstream-repo \
    ~/.workbuddy/skills/my-skill \
    --root "$HOME/.workbuddy/skills/my-skill" \
    --python "$(command -v python3)" \
    --desc-file desc.json

# 4) 按 references/checklist.md 收尾验收
# 5) 打包成可跨机复制的技能包
python scripts/pack_skill.py ~/.workbuddy/skills/my-skill -o my-skill.zip
```

## 依赖

| 组件 | 依赖 |
|---|---|
| `SKILL.md`、`references/` | **无** —— 纯文本，方法与清单开箱可用 |
| `scripts/*.py` | **Python 3.8+，仅标准库**，不需要 `pip install` |
| 下载上游仓库 | `curl` + `tar` |

**没有 Python 也能用** —— 只是不能跑自动转换，`references/mapping.md` 的映射表照样可以手工照做。

## 六条铁律

1. 不注册超过 5 个/仓库的新技能 —— 走单入口 + 渐进式披露
2. `LICENSE` 必须原样保留 —— 上游是 MIT/Apache 就照搬，别丢
3. `SOURCE.md` 必写 —— 记上游地址、commit/日期、已做的全部改写
4. 危险开关一律不继承 —— `--dangerously-skip-permissions` 等建议必须删掉
5. 实跑验证 > 静态检查 —— 语法正确不代表能跑
6. 改完必须全目录复扫 —— 漏一个文件就等于没改

## 沉淀的实战坑

移植 `xbtlin/ai-berkshire`（22 个技能文件、15 个 Python 工具、61 MB 源码包）时踩到并已验证：

- 上游 21 个斜杠命令平铺成 `.md`，直接拷过去等于装 0 个技能
- `grep` 含反引号的模式**必须用单引号**，否则触发 bash 命令替换，把正则变残缺并刷出整个文件
- `agent_type` 会误命中合法的 `subagent_type`，复扫时必须精确匹配
- 批次改写后必须全目录复扫 —— 当时只改了 `investment-team.md`，漏了另外两个含同类写法的文件
- `codeload` 下大包 `--max-time 60` 会截断（571 KB/s × 60s ≈ 34 MB，实际 61 MB），
  必须给到 280s 以上，且解压前先用 `tarfile` 验证完整性
- `str.format()` 与模板里的字面 `{花括号}` 冲突 —— 改用 `.replace()` 占位符替换
- 语法检查通过 ≠ 能运行 —— 必须实跑至少一个真实业务工具

## 安装

仓库根目录执行（`<仓库>` 指本仓库所在路径）：

```
<仓库>\install.bat
```

或 macOS / Linux：

```bash
bash <仓库>/install.sh
```

装完**新开一个会话**才生效。详细说明见仓库根 `README.md`，出处与改写记录见 `SOURCE.md`。

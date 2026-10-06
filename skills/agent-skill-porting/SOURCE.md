# SOURCE — 出处与改写记录

## 来源

- **性质**：**原创**，无上游项目
- **实战来源**：`xbtlin/ai-berkshire`（21 个 Claude Code 斜杠命令 → 1 个 WorkBuddy 入口技能）的完整移植过程
- **建立日期**：2026-10-05
- **入库日期**：2026-10-06
- **许可**：MIT（见仓库根 `LICENSE`）

## 改写记录

### 2026-10-06 — 从独立分发包转入合集仓库

原形态：`C:\Users\PC\Desktop\agent-skill-porting-skill.zip`，顶层目录前缀 `agent-skill-porting/`。

| 改动 | 说明 |
|---|---|
| 目录位置 | `agent-skill-porting/` → `skills/agent-skill-porting/`（合集仓库约定） |
| `README.md` | 由「zip 解压安装说明」改写为「技能说明」：剥离分发话术，安装方式改指仓库根 `install.bat` / `install.sh`，补入格式差异对照表与六条铁律摘要 |
| `SOURCE.md` | **新增** —— 原包无此文件 |
| `SKILL.md` | **内容未改动** |
| `references/mapping.md` | **内容未改动** |
| `references/checklist.md` | **内容未改动** |
| `scripts/port_skill.py` | **内容未改动** |
| `scripts/pack_skill.py` | **内容未改动** |

## 实跑验证

### 2026-10-06（搬运后复验）

```
$ python scripts/port_skill.py scan ../tencent-docs-mcp-usage
=== 候选技能文件：1 个 ===
  有 frontmatter: 1 个
  无 frontmatter: 0 个  ← 全部需要补 WorkBuddy frontmatter
=== 需要人工判断的写法 === （无）
=== 内部路径引用（转换时会自动改写）===
  tools/ 0 处 / skills/ 0 处 / reports/ 0 处 / assets/ 0 处
下一步：编写 slug → description 的 JSON 映射，然后跑 convert
→ 退出码 0
```

- `port_skill.py`、`pack_skill.py` 均通过 `ast.parse` 语法检查
- 依赖统计：**2 个脚本全部纯标准库**（`os` / `re` / `sys` / `zipfile` / `pathlib` / `argparse` / `shutil` / `tempfile` 等），无需 `pip install`

> 未验证项：`convert` 全流程与 `pack_skill.py` 打包未在本次搬运中重跑（`convert` 需要真实上游仓库作为输入）。下次实际移植时补记。

## 上游同步

原创项目，无上游可同步。方法论若在其他移植实战中出现新坑，直接在 `SKILL.md` 与 `references/` 内追加，
并把新增的已验证经验登记到本文件。

## 许可

MIT。随附说明的移植对象（如 `ai-berkshire`）各自许可见对应技能包内的 `LICENSE`。

# SOURCE — 出处与改写记录

## 来源

- **性质**：**原创**，无上游项目
- **唯一来源**：本机 `~/.workbuddy/skills/local-offline-dashboard/`（2026-10-06 复制入库）
- **内容形态**：单文件技能（仅 `SKILL.md`）
- **许可**：MIT（见仓库根 `LICENSE`）

## 技能概述

从本机数据文件生成**自包含的离线 HTML 看板** —— 双击即开，不需要服务器、不需要网络。

架构三分：`data.json` → `build.py` → `board.html`（数据在构建时内联进 HTML 的惰性数据块）。
`refresh.bat` 提供一键重建。

踩坑来源是实做看板项目时踩到的：`file://` 下 `fetch()` 被跨域拦截、`</` 未转义导致数据块提前闭合、
Windows `.bat` 非 ASCII 内容引发编码损坏、枚举变更要同步三处否则静默失效等。

## 改写记录

### 2026-10-06 — 入库

| 改动 | 说明 |
|---|---|
| 目录位置 | `~/.workbuddy/skills/local-offline-dashboard/` → `skills/local-offline-dashboard/` |
| `SKILL.md` | **内容未改动**（原样搬入） |
| `SOURCE.md` | **新增**（本文件） |

未做脱敏 —— 全文扫描无凭证类内容（无密码 / token / cookie / 内网 IP / 账号）。
`SKILL.md` 中出现的示例路径为通用示例，不含真实私有路径。

## 实跑验证

本技能是纯文档型技能（无随附脚本），不涉及脚本实跑。
`SKILL.md` 中的代码片段（JSON 内联正则替换、`.bat` 模板）在实际看板项目中已验证可用。

## 上游同步

原创，无上游。

## 已知待办

`SKILL.md` 的 `handoff checklist` 有两项编号重复（出现两个 `5.`）。属排版问题，不影响语义，
未在入库时改动正文。下次修订本技能时顺手修正。

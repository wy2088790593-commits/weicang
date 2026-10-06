# WorkBuddy 技能仓库

个人维护的 WorkBuddy 技能合集。只收**原创**或**已注明上游**的技能，不收来源不明的第三方市场包。

> 🔒 私有仓库。仅本人及被授权协作者可见。

## 技能清单

| 技能 | 用途 | 什么时候会触发 |
|---|---|---|
| [`agent-skill-porting`](skills/agent-skill-porting/) | 把第三方 agent skill 仓库（Claude Code / Codex / 任意 SKILL.md 集合）机械转换成 WorkBuddy 可加载技能 | 「把这个 skill 装上」「移植/转换/适配这个技能包」「skill 装不上」 |
| [`local-offline-dashboard`](skills/local-offline-dashboard/) | 从本机数据文件生成自包含的离线 HTML 看板，双击即开，不需要服务器和网络 | 「做个本地看板」「双击就能看的速查页」「投放决策看板/进度看板」 |
| [`tencent-docs-mcp-usage`](skills/tencent-docs-mcp-usage/) | 腾讯文档 MCP（个人版）接口的正确用法与实测踩坑，覆盖智能表格与在线表格 | 需要用 API 创建/写入腾讯文档、写公式、批量灌数 |

每个技能的详情看它自己的 `README.md`，改写与出处看 `SOURCE.md`。

## 安装

### Windows

双击 `install.bat`，或命令行：

```
install.bat            :: 复制安装（默认，安全）
install.bat link       :: 目录联接安装，改仓库即生效、不占双份空间
install.bat list       :: 只列出仓库里的技能，不安装
```

### macOS / Linux

```bash
bash install.sh           # 复制安装
bash install.sh link      # 符号链接安装
bash install.sh list
```

安装逻辑：把 `skills/<name>/` 放到 `~/.workbuddy/skills/<name>/`（Windows 为 `C:\Users\<你>\.workbuddy\skills\<name>\`）。

> ⚠️ **装完要新开一个会话才生效** —— 技能列表在会话启动时加载。

两种安装方式的差别：

| 方式 | 原理 | 适合 |
|---|---|---|
| 复制 | 把文件拷进技能目录 | 稳定，改仓库不影响已装版本；缺点是两份副本要同步 |
| link | `mklink /J`（Windows）/ `ln -s`（Unix）目录联接 | 仓库即技能目录，改完立即可用；Windows 下建议放在纯英文路径 |

## 目录约定

```
.
├── README.md              这个文件
├── LICENSE                MIT
├── .gitignore
├── install.bat            Windows 安装（GBK + CRLF，内容纯 ASCII）
├── install.sh             macOS / Linux 安装
└── skills/
    └── <skill-name>/
        ├── SKILL.md       ← 必需。WorkBuddy 只认这个层级的 SKILL.md
        ├── README.md      技能说明 + 安装注意
        ├── SOURCE.md      出处、改写记录、实跑验证（原创技能写"无上游"）
        ├── references/    可选。渐进式披露的参考资料，按需读取
        ├── scripts/       可选。脚本
        └── tools/         可选。业务工具
```

**关键约束**：WorkBuddy 只注册技能根目录下**一级**的 `SKILL.md`。子目录里的文件不会被单独注册，只能被主技能按需 `Read` —— 这正是「单入口 + 渐进式披露」的用法。

## 收录标准

新技能入库前必须过这几条：

1. **来源清楚** —— 原创，或已取得上游授权许可。第三方市场包一律不入库
2. **`SKILL.md` frontmatter 合规** —— `name` / `description` / `agent_created`
3. **`description` 写清"做什么 + 什么场景触发"** —— 它是路由命中的唯一依据，不能写成 `TODO`
4. **`SOURCE.md` 必写** —— 上游地址、版本日期、做过的全部改写、实跑验证记录
5. **上游 `LICENSE` 原样保留** —— 改编他人项目时必须带上
6. **无凭证** —— 密码、cookie、token、内网 IP 一律清掉；业务型技能单独走私有仓

## 怎么加一个新技能

```bash
# 1) 从本机已装技能复制，或从零新建
cp -r ~/.workbuddy/skills/<name> skills/<name>

# 2) 清理不该进仓库的东西
#    __pycache__ / *.pyc / _skillhub_meta.json / 含凭证的内容

# 3) 补 SOURCE.md（出处 + 改写记录 + 实跑验证）

# 4) 更新本文件的技能清单表

# 5) 提交
git add -A && git commit -m "add skill: <name>"
```

## 许可

本仓库除各技能目录内单独声明的部分外，采用 [MIT License](LICENSE) 授权。
改编自上游项目的技能，其上游许可见对应技能目录下的 `LICENSE` 与 `SOURCE.md`。

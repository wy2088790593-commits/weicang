#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
port_skill.py —— 把第三方 agent skill 仓库（Claude Code / Codex 格式）移植成 WorkBuddy 技能。

两个模式：

  scan    <src_dir>                      诊断报告：有哪些文件、哪些需要手工改写
  convert <src_dir> <dst_dir> [选项]      机械转换：加 frontmatter、改写路径与专有工具名

选项（convert）：
  --root <路径>       技能根目录，用于替换 {SKILL_ROOT}（默认取 dst_dir 的绝对路径）
  --python <路径>     写进适配说明的 Python 解释器路径
  --desc-file <json>  slug -> 描述的映射（JSON），用于生成 frontmatter 的 description
  --emit-note         在每个文件顶部插入适配说明注释块（默认开启）

用法示例：

  python port_skill.py scan  ./upstream
  python port_skill.py convert ./upstream ~/.workbuddy/skills/my-skill \
      --root "$HOME/.workbuddy/skills/my-skill" --python "$(which python3)"
"""
import argparse, io, json, os, re, shutil, sys

# ── Claude Code / Codex 专有写法 → WorkBuddy 映射 ──────────────────────────
# 形式：(正则, 替换串, 说明)
TOOL_MAP = [
    (r"Task\s*工具",      "Agent 工具",  "Task 工具 → Agent 工具"),
    (r"Team\s*工具",      "Agent 工具",  "Team 工具 → Agent 工具"),
    (r"使用 TeamCreate 创建团队：", "WorkBuddy 无需预先创建团队对象，你本人即 team-lead：",
     "TeamCreate → 无团队对象，靠并发 Agent 调用"),
    (r"- `team_name`:",   "- `name`:",   "team_name 参数 → name 参数"),
    (r"- team_name:",     "- name:",     "team_name 参数 → name 参数"),
    (r"- `agent_type`: `team-lead`", "- 子代理类型：`general-purpose`", "agent_type → subagent_type"),
    (r"- agent_type: `team-lead`",   "- 子代理类型：`general-purpose`", "agent_type → subagent_type"),
    (r"全部报告收到后，向4个Agent发送 shutdown_request（使用 SendMessage，type: \"shutdown_request\"）。",
     "全部报告收到即可直接汇总。WorkBuddy 的子代理在返回结果后自然结束，无需显式的关闭握手。",
     "shutdown_request → 自然结束"),
    (r"通过 SendMessage 把完整分析报告发送给 team-lead（type: \"message\", recipient: \"team-lead\"）",
     "把完整分析报告作为最终返回值输出（WorkBuddy 中子代理的返回值会自动回到主代理）",
     "SendMessage 汇报 → 返回值"),
]

# 路径前缀替换：仓库根相对路径 → {SKILL_ROOT}
PATH_MAP = ["tools/", "skills/", "reports/", "assets/"]

# 需要人工判断的关键词（scan 阶段高亮）
NEEDS_REVIEW = {
    r"\.claude/settings":     "Claude 权限白名单配置，需改写为「联网能力预检」",
    r"\.codex/":              "Codex 目录约定，需确认是否适用",
    r"CLAUDE\.md":            "项目规范文件引用，需改指新位置",
    r"AGENTS\.md":            "项目规范文件引用，需改指新位置",
    r"dangerously-skip-permissions": "危险开关，移植后不应保留建议",
    r"TeamCreate|shutdown_request":  "团队编排写法，转换脚本可处理",
    r"\$ARGUMENTS":           "斜杠命令参数，需在适配说明中解释",
}

ADAPT_NOTE = """<!-- WorkBuddy 适配说明
  $ARGUMENTS   = 用户本轮指定的标的 / 主题，执行时替换为实际值
  {SKILL_ROOT} = __ROOT__
  Python       = __PY__
  文中「Agent 工具」= WorkBuddy 的并行子代理，在同一条消息内并发调用多次即可真正并行
-->

"""


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def write(p, s):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)


def die(msg):
    sys.stderr.write("[FAIL] %s\n" % msg)
    sys.exit(2)


def require_src(src):
    """源目录不存在时立刻报错 —— os.walk 对不存在的目录只会静默返回空，
    容易把「路径写错」误判成「上游没有技能文件」。"""
    if not os.path.isdir(src):
        die("源目录不存在或不是目录：%s" % os.path.abspath(src))


def find_skill_files(src):
    """找出候选技能文件：*.md，且带一级标题。"""
    out = []
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
        for f in sorted(files):
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return out


# ─────────────────────────── scan ───────────────────────────
def cmd_scan(a):
    src = a.src
    require_src(src)
    files = find_skill_files(src)
    print("=== 候选技能文件：%d 个 ===" % len(files))
    print()
    no_fm, has_fm = [], []
    for p in files:
        t = read(p)
        (has_fm if re.match(r"^---\s*\n", t) else no_fm).append(p)
    print("  有 frontmatter: %d 个" % len(has_fm))
    print("  无 frontmatter: %d 个  ← 全部需要补 WorkBuddy frontmatter" % len(no_fm))
    print()

    print("=== 需要人工判断的写法 ===")
    agg = {}
    for p in files:
        t = read(p)
        for pat, why in NEEDS_REVIEW.items():
            n = len(re.findall(pat, t))
            if n:
                agg.setdefault(why, []).append((os.path.relpath(p, src), n))
    if not agg:
        print("  （无）")
    for why, hits in sorted(agg.items(), key=lambda x: -sum(h[1] for h in x[1])):
        total = sum(h[1] for h in hits)
        print("  %-46s %3d 处 / %d 个文件" % (why, total, len(hits)))
        for name, n in hits[:4]:
            print("      %-56s %d" % (name, n))
        if len(hits) > 4:
            print("      ... 另有 %d 个文件" % (len(hits) - 4))
    print()

    print("=== 内部路径引用（转换时会自动改写）===")
    for pre in PATH_MAP:
        cnt = sum(len(re.findall(r"(?<![\w\-/{])" + re.escape(pre), read(p))) for p in files)
        print("  %-12s %d 处" % (pre, cnt))
    print()

    print("=== 其它内容 ===")
    for sub in ("tools", "scripts", "assets", "data", "references"):
        d = os.path.join(src, sub)
        if os.path.isdir(d):
            n = sum(len(fs) for _, _, fs in os.walk(d))
            print("  %-12s %d 个文件" % (sub + "/", n))
    print()
    print("下一步：编写 slug → description 的 JSON 映射，然后跑 convert")


# ─────────────────────────── convert ───────────────────────────
def cmd_convert(a):
    src, dst = a.src, a.dst
    require_src(src)
    root = a.root or os.path.abspath(dst)
    py = a.python or sys.executable

    desc = {}
    if a.desc_file and os.path.exists(a.desc_file):
        desc = json.load(io.open(a.desc_file, encoding="utf-8"))
    elif a.desc_file:
        print("[WARN] --desc-file 指向的文件不存在：%s（将全部填 TODO）" % a.desc_file)

    # --root 会被写进每个子技能的适配说明注释块；与 dst 不一致通常意味着写错，
    # 换机后这些绝对路径全部失效 —— 必须提醒。
    if os.path.abspath(root) != os.path.abspath(dst):
        print("[WARN] --root(%s) 与目标目录(%s) 不一致，" % (root, os.path.abspath(dst)))
        print("       写进适配说明的绝对路径可能与实际安装位置不符，请确认。")
        print()

    skill_dir = os.path.join(dst, "references", "skills")
    os.makedirs(skill_dir, exist_ok=True)
    for sub in ("tools", "assets", "reports"):
        os.makedirs(os.path.join(dst, sub), exist_ok=True)

    files = [p for p in find_skill_files(src) if os.sep + "tools" + os.sep not in p]
    note = ADAPT_NOTE.replace("__ROOT__", root).replace("__PY__", py)
    done, warned = [], []

    for p in files:
        slug = os.path.splitext(os.path.basename(p))[0]
        t = read(p)
        # 1) 去掉旧 frontmatter
        t = re.sub(r"^---\s*\n.*?\n---\s*\n", "", t, count=1, flags=re.S)
        # 2) 路径改写
        for pre in PATH_MAP:
            t = re.sub(r"(?<![\w\-/{])" + re.escape(pre), "{SKILL_ROOT}/" + pre, t)
        # 3) 专有工具名改写
        for pat, rep, _ in TOOL_MAP:
            t = re.sub(pat, rep, t)
        # 4) frontmatter
        d = desc.get(slug)
        if not d:
            warned.append(slug)
            d = "TODO: 补充该技能的一句话说明（用于路由匹配）。"
        fm = "---\nname: %s\ndescription: %s\nagent_created: true\n---\n\n" % (slug, d)
        write(os.path.join(skill_dir, os.path.basename(p)), fm + note + t.lstrip("\n"))
        done.append(slug)

    # 复制工具目录
    for sub in ("tools", "scripts"):
        s = os.path.join(src, sub)
        if os.path.isdir(s):
            for f in sorted(os.listdir(s)):
                fp = os.path.join(s, f)
                if os.path.isfile(fp) and not f.endswith(".pyc"):
                    shutil.copy2(fp, os.path.join(dst, "tools", f))
    for f in ("LICENSE", "LICENSE.md"):
        fp = os.path.join(src, f)
        if os.path.isfile(fp):
            shutil.copy2(fp, os.path.join(dst, "LICENSE"))

    print("转换完成 → %s" % dst)
    print("  子技能: %d 个" % len(done))
    print("  tools/: %d 个文件" % len(os.listdir(os.path.join(dst, "tools"))))
    if warned:
        print()
        print("  !! 以下 %d 个技能缺少 description 映射，已填 TODO，必须补：" % len(warned))
        for w in warned:
            print("     ", w)
    unused = sorted(set(desc) - set(done))
    if unused:
        print()
        print("  !! desc 映射里有 %d 个键没有对应技能（多半是拼写错误，或 .md 文件名对不上）：" % len(unused))
        for u in unused:
            print("     ", u)
    print()
    print("后续必做（脚本不做）：")
    print("  1. 手写路由层 SKILL.md（索引表 + 调用协议 + 铁律）")
    print("  2. 补回缺 description 的技能")
    print("  3. 全目录复扫专有写法残留，不能只验抽样文件")
    print("  4. 实跑至少一个工具，确认端到端可用")


def main():
    ap = argparse.ArgumentParser(description="移植第三方 agent skill 到 WorkBuddy")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="诊断报告")
    s.add_argument("src")
    s.set_defaults(func=cmd_scan)

    c = sub.add_parser("convert", help="执行转换")
    c.add_argument("src")
    c.add_argument("dst")
    c.add_argument("--root", default=None)
    c.add_argument("--python", default=None)
    c.add_argument("--desc-file", default=None)
    c.set_defaults(func=cmd_convert)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()

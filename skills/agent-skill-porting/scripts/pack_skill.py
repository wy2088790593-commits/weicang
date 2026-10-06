#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pack_skill.py —— 把一个 WorkBuddy 技能目录打包成可移植 zip，并自动校验。

用法：
  python pack_skill.py <skill_dir> [-o 输出.zip] [--no-verify]

默认输出：<skill_dir 名>-skill.zip（放在当前目录）

做三件事：
  1. 打包：保留顶层目录前缀（zip 内路径为 <name>/...），跳过 __pycache__/.pyc/.git/.DS_Store
  2. 校验：zip 完整性 testzip()、SKILL.md 层级、frontmatter 必填字段
  3. 解压演练：解到临时目录，确认 SKILL.md 落在 <name>/SKILL.md，且脚本可执行
"""
import argparse, io, os, re, shutil, sys, tempfile, zipfile

SKIP_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules"}
SKIP_EXT = {".pyc", ".pyo", ".DS_Store", ".zip"}
REQUIRED_FM = ("name", "description", "agent_created")


def want(fp):
    name = os.path.basename(fp)
    if name in (".DS_Store",) or name.endswith(".pyc"):
        return False
    return True


def build(skill_dir, out_zip):
    skill_dir = os.path.abspath(skill_dir.rstrip("/\\"))
    top = os.path.basename(skill_dir)
    n = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, dirs, files in os.walk(skill_dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                fp = os.path.join(dp, f)
                if not want(fp):
                    continue
                rel = os.path.relpath(fp, skill_dir).replace(os.sep, "/")
                z.write(fp, top + "/" + rel)   # ← 保留顶层前缀，关键
                n += 1
    return top, n


def verify(out_zip, top):
    print("== 校验 ==")
    ok = True
    with zipfile.ZipFile(out_zip) as z:
        bad = z.testzip()
        if bad:
            print("  [FAIL] zip 损坏，首个坏文件: %s" % bad); ok = False
        else:
            print("  [ OK ] zip 完整性通过")

        names = z.namelist()
        entry = top + "/SKILL.md"
        if entry not in names:
            print("  [FAIL] 未找到 %s（顶层前缀可能丢失）" % entry); ok = False
        else:
            print("  [ OK ] 入口层级正确: %s" % entry)

        top_dirs = {x.split("/")[0] for x in names if "/" in x}
        if top_dirs != {top}:
            print("  [FAIL] zip 内顶层目录不唯一: %s" % top_dirs); ok = False
        else:
            print("  [ OK ] zip 内顶层目录唯一: %s/" % top)

        if entry in names:
            head = z.read(entry).decode("utf-8", "replace")[:600]
            m = re.match(r"^---\s*\n(.*?)\n---", head, re.S)
            if not m:
                print("  [FAIL] SKILL.md 缺 frontmatter"); ok = False
            else:
                fm = m.group(1)
                miss = [k for k in REQUIRED_FM if not re.search(r"^%s\s*:" % k, fm, re.M)]
                if miss:
                    print("  [FAIL] frontmatter 缺字段: %s" % ", ".join(miss)); ok = False
                else:
                    print("  [ OK ] frontmatter 含 name/description/agent_created")
                d = re.search(r"^description\s*:\s*(.+)$", fm, re.M)
                if d and d.group(1).strip().startswith("TODO"):
                    print("  [WARN] description 仍是 TODO 占位，技能不会被路由命中")
    return ok


def dry_run(out_zip, top):
    print("== 解压演练 ==")
    tmp = tempfile.mkdtemp(prefix="packcheck_")
    try:
        with zipfile.ZipFile(out_zip) as z:
            z.extractall(tmp)
        d = os.path.join(tmp, top)
        sm = os.path.join(d, "SKILL.md")
        if not os.path.isfile(sm):
            print("  [FAIL] 解压后 %s/SKILL.md 不存在" % top); return False
        print("  [ OK ] 解压后结构正确: %s/SKILL.md" % top)
        import py_compile
        for sub in ("scripts", "tools"):
            sd = os.path.join(d, sub)
            if not os.path.isdir(sd):
                continue
            py = sorted(f for f in os.listdir(sd) if f.endswith(".py"))
            if not py:
                continue
            bad = []
            for f in py:
                try:
                    py_compile.compile(os.path.join(sd, f), doraise=True)
                except Exception as e:
                    print("  [FAIL] %s/%s 编译失败: %s" % (sub, f, e))
                    bad.append(f)
            if not bad:
                print("  [ OK ] %s/ 下 %d 个脚本编译通过" % (sub, len(py)))
            else:
                return False
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="打包 WorkBuddy 技能目录并校验")
    ap.add_argument("skill_dir")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()

    skill_dir = os.path.abspath(a.skill_dir)
    if not os.path.isfile(os.path.join(skill_dir, "SKILL.md")):
        print("[FAIL] %s 下没有 SKILL.md，不是一个 WorkBuddy 技能目录" % skill_dir)
        sys.exit(2)

    top = os.path.basename(skill_dir)
    out_zip = a.out or (top + "-skill.zip")

    top, n = build(skill_dir, out_zip)
    size = os.path.getsize(out_zip)
    print("打包完成 → %s" % os.path.abspath(out_zip))
    print("  顶层目录: %s/" % top)
    print("  文件数: %d" % n)
    print("  体积: %.1f KB" % (size / 1024.0))
    print()

    if a.no_verify:
        return
    ok = verify(out_zip, top)
    print()
    ok = dry_run(out_zip, top) and ok
    print()
    print("结果：%s" % ("全部通过，可以分发" if ok else "存在 FAIL，请修复后重打"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""按归档计划把源文件复制成归档单元。

计划文件 plan.csv（UTF-8 带 BOM 也可以），表头固定五行：
    期限,部门,序号,题名,源路径
    永久,办公室（党委办公室、党委工作部）,0053,九建公司2025年发文登记簿,Z:\\...\\2025年发文记录表-九建公司.xlsx

用法：
    python copy_units.py --plan plan.csv --root "Z:\\...\\2025年" --dry-run
    python copy_units.py --plan plan.csv --root "Z:\\...\\2025年"

- 目标：<root>\\<期限>\\<部门>\\<序号>-<题名>\\
- 源路径是文件 -> 复制进单元；是目录 -> 目录内容整体复制进单元
- 已存在的同名文件跳过（不会覆盖，可重复运行）
- 源不存在直接报错，不会建空单元
"""
import argparse
import csv
import datetime
import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIELDS = ["期限", "部门", "序号", "题名", "源路径"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--log", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-hyphen", action="store_true", help="单元名不用 序号-题名，改为 序号题名")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("[错误] 归档根目录不存在：%s" % root)
        return 2

    rows = []
    with open(args.plan, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if not r or not (r.get("源路径") or "").strip():
                continue
            rows.append({k: (r.get(k) or "").strip() for k in FIELDS})

    lines = []
    def say(m):
        print(m)
        lines.append(m)

    say("=" * 66)
    say("开始：%s  模式：%s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "预览" if args.dry_run else "实际复制"))
    say("计划 %d 条，归档根目录 %s" % (len(rows), root))
    say("=" * 66)

    ok = skip = fail = 0
    for i, r in enumerate(rows, 1):
        period, dept, seq, title, src = r["期限"], r["部门"], r["序号"], r["题名"], r["源路径"]
        if not os.path.exists(src):
            say("✗ [源不存在] %s" % src)
            fail += 1
            continue
        if os.path.abspath(src).startswith(root):
            say("✗ [拒绝] 源在归档目录内，可能是自己抄自己：%s" % src)
            fail += 1
            continue
        name = ("%s%s" % (seq, title)) if args.no_hyphen else ("%s-%s" % (seq, title))
        target = os.path.join(root, period, dept, name)

        if os.path.isdir(src):
            n = sum(len(fs) for _, _, fs in os.walk(src))
        else:
            n = 1

        if args.dry_run:
            say("[%d/%d] %s / %s / %s  <- %d 项" % (i, len(rows), period, dept, name, n))
            ok += 1
            continue

        try:
            os.makedirs(target, exist_ok=True)
            if os.path.isdir(src):
                copied = 0
                for dp, _, fs in os.walk(src):
                    rel = os.path.relpath(dp, src)
                    dst_dir = target if rel == "." else os.path.join(target, rel)
                    os.makedirs(dst_dir, exist_ok=True)
                    for fn in fs:
                        dst = os.path.join(dst_dir, fn)
                        if os.path.exists(dst):
                            continue
                        shutil.copy2(os.path.join(dp, fn), dst)
                        copied += 1
                say("✓ %s / %s" % (name, "复制 %d 个文件" % copied))
            else:
                dst = os.path.join(target, os.path.basename(src))
                if os.path.exists(dst):
                    say("- %s（已存在，跳过）" % name)
                    skip += 1
                    continue
                shutil.copy2(src, dst)
                say("✓ %s / %s" % (name, os.path.basename(src)))
            ok += 1
        except Exception as e:
            say("✗ [失败] %s :: %s" % (name, e))
            fail += 1

    say("-" * 66)
    say("完成：成功 %d，跳过 %d，失败 %d" % (ok, skip, fail))

    if args.log and not args.dry_run:
        with open(args.log, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n" + "=" * 66 + "\n\n")
        print("日志：%s" % args.log)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
